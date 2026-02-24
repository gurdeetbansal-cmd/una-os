/**
 * UNA + Shopify Buy Button Integration
 * Syncs Shopify cart to UNA drawer, custom Add to Bag trigger, variant ID bridge.
 */
(function() {
  'use strict';

  var config = window.UNA_SHOPIFY_CONFIG;
  if (!config || !config.domain || !config.storefrontAccessToken) return;

  /** Variant IDs for Add to Cart – used by data-shopify-variant-id and JS bridge */
  window.UNA_SHOPIFY_VARIANT_IDS = {
    'reset-foaming-cleanser': '15298500788601',
    'signal-serum': '15147129373049',
    'seal-cream': '15298501804409'
  };

  /** Product title to dedicated page path (for cart drawer links) */
  var TITLE_TO_PAGE = {
    'Reset Foaming Cleanser': 'reset-cleanser.html',
    'Signal Serum': 'signal-serum.html',
    'Seal Cream': 'seal-cream.html'
  };

  function getProductPageUrl(title) {
    var slug = title && TITLE_TO_PAGE[title];
    if (!slug) return null;
    var inPages = window.location.pathname.indexOf('pages/') !== -1;
    return inPages ? slug : 'pages/' + slug;
  }

  var client = null;
  var ui = null;
  var cartComponent = null;
  var VARIANT_GID_PREFIX = 'gid://shopify/ProductVariant/';
  var PRODUCT_GID_PREFIX = 'gid://shopify/Product/';

  function formatMoney(cents, currency) {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: currency || 'USD'
    }).format(cents / 100);
  }

  function syncCartToUNADrawer(cartModel) {
    var cartDrawer = document.getElementById('cart-drawer');
    var itemsEl = document.querySelector('.cart-drawer__items');
    var emptyState = document.querySelector('.cart-drawer__empty-state');
    var subtotalSpan = document.querySelector('.cart-drawer__subtotal span');
    var checkoutBtn = document.querySelector('.cart-drawer__checkout');
    var cartCount = document.querySelector('.cart-count');

    if (!itemsEl || !cartDrawer) return;

    var rawItems = cartModel && (typeof cartModel.lineItems === 'function' ? cartModel.lineItems() : cartModel.lineItems);
    var lineItems = Array.isArray(rawItems) ? rawItems : [];
    var itemCount = lineItems.reduce(function(sum, li) { return sum + (li.quantity || 0); }, 0);

    if (cartCount) cartCount.textContent = itemCount;

    if (itemCount === 0) {
      if (emptyState) emptyState.style.display = '';
      var list = itemsEl.querySelector('.cart-drawer__line-items');
      if (list) list.remove();
      if (subtotalSpan) subtotalSpan.textContent = '$0.00';
      if (checkoutBtn) {
        checkoutBtn.disabled = true;
        checkoutBtn.removeAttribute('href');
        checkoutBtn.onclick = null;
      }
      return;
    }

    if (emptyState) emptyState.style.display = 'none';

    var list = itemsEl.querySelector('.cart-drawer__line-items');
    if (!list) {
      list = document.createElement('div');
      list.className = 'cart-drawer__line-items';
      itemsEl.insertBefore(list, emptyState);
    }
    list.innerHTML = '';

    var currency = (cartModel && (cartModel.currency || (cartModel.attrs && cartModel.attrs.currency))) || 'USD';
    lineItems.forEach(function(lineItem) {
      var title = lineItem.title || (lineItem.attrs && lineItem.attrs.title);
      var variantTitle = lineItem.variantTitle || (lineItem.attrs && lineItem.attrs.variantTitle);
      var quantity = lineItem.quantity || 1;
      var variant = lineItem.variant || (lineItem.attrs && lineItem.attrs.variant);
      var price = variant && (variant.price != null) ? variant.price : (lineItem.price != null ? lineItem.price : 0);
      var img = (lineItem.image && lineItem.image.src) ? lineItem.image.src : (lineItem.attrs && lineItem.attrs.image && lineItem.attrs.image.src) ? lineItem.attrs.image.src : '';
      var productUrl = getProductPageUrl(title);
      var imgWrap = productUrl
        ? '<a href="' + productUrl + '" class="cart-drawer__line-item__img-link" aria-label="View ' + (title || 'product') + '"><div class="cart-drawer__line-item__img" style="background-image:url(' + (img || '') + ')"></div></a>'
        : '<div class="cart-drawer__line-item__img" style="background-image:url(' + (img || '') + ')"></div>';
      var titleWrap = productUrl
        ? '<a href="' + productUrl + '" class="cart-drawer__line-item__title-link">' + (title || '') + '</a>'
        : '<span class="cart-drawer__line-item__title">' + (title || '') + '</span>';

      var li = document.createElement('div');
      li.className = 'cart-drawer__line-item';
      li.innerHTML =
        imgWrap +
        '<div class="cart-drawer__line-item__info">' +
          titleWrap +
          (variantTitle ? '<span class="cart-drawer__line-item__variant">' + variantTitle + '</span>' : '') +
          '<span class="cart-drawer__line-item__price">' + formatMoney(price, currency) + ' × ' + quantity + '</span>' +
        '</div>';
      list.appendChild(li);
    });

    var total = (cartModel && (cartModel.subtotal != null ? cartModel.subtotal : (cartModel.attrs && cartModel.attrs.subtotal))) || 0;
    if (subtotalSpan) subtotalSpan.textContent = formatMoney(total, currency);

    if (checkoutBtn) {
      checkoutBtn.disabled = false;
      var checkoutUrl = (cartModel && (cartModel.checkoutUrl || (cartModel.attrs && cartModel.attrs.checkoutUrl))) || '';
      checkoutBtn.onclick = function(e) {
        e.preventDefault();
        if (checkoutUrl) window.location.href = checkoutUrl;
      };
    }
  }

  function openUNADrawer() {
    var cartDrawer = document.getElementById('cart-drawer');
    var cartOverlay = document.getElementById('cart-overlay');
    if (cartDrawer && cartOverlay) {
      cartDrawer.classList.add('active');
      cartOverlay.classList.add('active');
      cartDrawer.setAttribute('aria-hidden', 'false');
      cartOverlay.setAttribute('aria-hidden', 'false');
      document.body.style.overflow = 'hidden';
    }
  }

  /** Get numeric ID from GID (e.g. gid://shopify/Product/123 -> 123) */
  function gidToNumericId(gid) {
    if (!gid) return null;
    var parts = String(gid).split('/');
    return parts.length ? parts[parts.length - 1] : null;
  }

  /**
   * Add a variant to the Shopify cart by variant ID (numeric).
   * Uses Storefront API to resolve variant, then SDK cart to add.
   */
  function addVariantToCartByVariantId(variantId, quantity) {
    quantity = quantity || 1;
    if (!variantId || !client) return Promise.reject(new Error('Missing variantId or client'));

    var variantGid = VARIANT_GID_PREFIX + String(variantId).trim();

    return fetch('https://' + config.domain + '/api/2024-01/graphql.json', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Shopify-Storefront-Access-Token': config.storefrontAccessToken
      },
      body: JSON.stringify({
        query: 'query GetProductId($id: ID!) { node(id: $id) { ... on ProductVariant { id product { id } } } }',
        variables: { id: variantGid }
      })
    })
      .then(function(res) { return res.json(); })
      .then(function(data) {
        var node = data && data.data && data.data.node;
        if (!node || !node.product || !node.product.id) return Promise.reject(new Error('Variant not found'));
        return gidToNumericId(node.product.id);
      })
      .then(function(productId) {
        return client.product.fetch(productId);
      })
      .then(function(product) {
        var variants = product.variants || (product.attrs && product.attrs.variants) || [];
        var variant = null;
        for (var i = 0; i < variants.length; i++) {
          var v = variants[i];
          var vId = (v.id != null ? v.id : (v.attrs && v.attrs.id));
          if (vId == variantId || String(vId).indexOf(variantId) !== -1) {
            variant = v;
            break;
          }
        }
        if (!variant && variants.length) variant = variants[0];
        if (!variant) return Promise.reject(new Error('Variant not found on product'));
        return variant;
      })
      .then(function(variant) {
        if (!cartComponent || !cartComponent.model) return Promise.reject(new Error('Cart not ready'));
        if (typeof cartComponent.model.addVariants !== 'function') return Promise.reject(new Error('Cart addVariants not available'));
        return cartComponent.model.addVariants([variant], quantity);
      })
      .then(function() {
        if (cartComponent && cartComponent.model) syncCartToUNADrawer(cartComponent.model);
        openUNADrawer();
      });
  }

  /** Global bridge: call from any Add to Cart button with variant ID */
  window.UNAAddVariantToCart = function(variantId, quantity) {
    return addVariantToCartByVariantId(variantId, quantity);
  };

  function initCart() {
    var cartNode = document.getElementById('shopify-cart-node');
    if (!cartNode) {
      cartNode = document.createElement('div');
      cartNode.id = 'shopify-cart-node';
      cartNode.style.cssText = 'position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden;';
      document.body.appendChild(cartNode);
    }

    return ShopifyBuy.UI.createComponent('cart', {
      node: cartNode,
      options: {
        cart: {
          iframe: false,
          contents: { title: false, lineItems: false, footer: false },
          startOpen: false,
          events: {
            updateItemQuantity: function(cart) { if (cart && cart.model) syncCartToUNADrawer(cart.model); },
            openCheckout: function(cart) { if (cart && cart.model) syncCartToUNADrawer(cart.model); }
          }
        },
        toggle: { contents: { count: false, icon: false, title: false } }
      }
    }).then(function(components) {
      var cart = Array.isArray(components) ? components[0] : components;
      cartComponent = cart;
      if (cart && cart.model) syncCartToUNADrawer(cart.model);
      if (cart && cart.model && typeof cart.model.on === 'function') {
        cart.model.on('change', function() { syncCartToUNADrawer(cart.model); });
      }
      return cart;
    }).catch(function() { return null; });
  }

  function initProductPage() {
    var container = document.querySelector('[data-shopify-product-id]');
    if (!container) return Promise.resolve();

    var productId = container.getAttribute('data-shopify-product-id');
    if (!productId || productId === 'REPLACE_WITH_PRODUCT_ID' || /^\s*$/.test(productId)) return Promise.resolve();
    productId = productId.trim();
    var addBtn = container.querySelector('.product-info__btn:not(.product-info__btn--secondary)');
    var priceEl = container.querySelector('.product-info__price');
    var titleEl = container.querySelector('.product-info__title');
    var descEl = container.querySelector('.product-info__description');
    var availabilityEl = container.querySelector('.product-info__availability');
    var optionsWrapper = container.querySelector('.product-info__options');

    var productNode = document.createElement('div');
    productNode.className = 'shopify-product-trigger';
    productNode.style.cssText = 'position:relative;display:inline-block;width:100%;';
    if (addBtn && addBtn.parentNode) {
      addBtn.parentNode.insertBefore(productNode, addBtn);
      productNode.appendChild(addBtn);
    }

    var triggerInner = document.createElement('div');
    triggerInner.id = 'shopify-product-inner';
    triggerInner.style.cssText = 'position:absolute;top:0;left:0;width:100%;height:100%;';
    productNode.appendChild(triggerInner);

    return ShopifyBuy.UI.createComponent('product', {
      id: productId,
      node: triggerInner,
      options: {
        product: {
          iframe: false,
          buttonDestination: 'cart',
          contents: {
            img: false,
            title: false,
            variantTitle: false,
            price: false,
            options: true,
            quantity: false,
            button: true,
            description: false
          },
          order: ['options', 'button'],
          styles: {
            button: {
              position: 'absolute',
              top: '0',
              left: '0',
              width: '100%',
              height: '100%',
              opacity: '0',
              cursor: 'pointer',
              margin: '0',
              padding: '0',
              border: 'none',
              'font-size': 'inherit'
            }
          },
          events: {
            afterRender: function(component) {
              var model = component.model;
              if (!model) return;
              var variant = model.selectedVariant;
              if (priceEl && variant) priceEl.textContent = formatMoney(variant.price, variant.currency);
              if (titleEl && model.title) titleEl.textContent = model.title;
              if (descEl && model.description) descEl.textContent = model.description.replace(/<[^>]+>/g, '').trim();
              if (availabilityEl) {
                availabilityEl.textContent = variant && variant.available ? 'In stock' : 'Out of stock';
                availabilityEl.classList.toggle('product-info__availability--out', !(variant && variant.available));
              }
              if (optionsWrapper && model.variants && model.variants.length > 1) {
                optionsWrapper.style.display = '';
              }
            },
            addVariantToCart: function() {
              openUNADrawer();
              setTimeout(function() {
                if (cartComponent && cartComponent.model) syncCartToUNADrawer(cartComponent.model);
              }, 150);
            }
          }
        },
        cart: { contents: { title: false, lineItems: false, footer: false }, startOpen: false },
        toggle: { contents: { count: false, icon: false, title: false } }
      }
    }).then(function(components) {
      var product = Array.isArray(components) ? components[0] : components;
      if (!cartComponent) return initCart().then(function() { return product; });
      return product;
    }).then(function(product) {
      if (product && product.model) {
        product.model.on('variantChange', function() {
          var v = product.model.selectedVariant;
          if (priceEl && v) priceEl.textContent = formatMoney(v.price, v.currency);
          if (availabilityEl) {
            availabilityEl.textContent = v && v.available ? 'In stock' : 'Out of stock';
            availabilityEl.classList.toggle('product-info__availability--out', !(v && v.available));
          }
        });
      }
      return product;
    }).catch(function(err) {
      if (addBtn) addBtn.disabled = true;
      return initCart();
    });
  }

  /** Delegated click: any .una-add-to-cart with data-shopify-variant-id adds that variant */
  function bindVariantButtons() {
    document.addEventListener('click', function(e) {
      var btn = e.target && e.target.closest && e.target.closest('.una-add-to-cart');
      if (!btn) return;
      var variantId = btn.getAttribute('data-shopify-variant-id');
      if (!variantId) return;
      e.preventDefault();
      e.stopPropagation();
      addVariantToCartByVariantId(variantId.trim(), 1).catch(function(err) {
        if (typeof console !== 'undefined' && console.error) console.error('UNA Add to Cart:', err);
      });
    });
  }

  function init() {
    if (typeof ShopifyBuy === 'undefined') return;

    client = ShopifyBuy.buildClient({
      domain: config.domain,
      storefrontAccessToken: config.storefrontAccessToken
    });

    ui = ShopifyBuy.UI.init(client);

    bindVariantButtons();

    initCart().then(function() {
      if (document.querySelector('[data-shopify-product-id]')) {
        return initProductPage();
      }
    }).catch(function() {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
