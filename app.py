import streamlit as st
from google import genai
from google.genai import types
import pypdf
import PIL.Image
import requests
import urllib.parse
import random
import json
import re
import os
import uuid
from io import BytesIO

# ==========================================
# CONFIGURATION
# ==========================================

# Replace with your actual API keys
GOOGLE_API_KEY = "AIzaSyCyo7yphrahOkwHpQLD8le2FW8Y2-Xgn6M"
POLLINATIONS_API_KEY = "sk_yNHgkvTQpFMr5J0PMkGtDkgABITMT3kL"

# ==========================================
# SYSTEM BRAIN: THE FORTRESS DIRECTIVE (v18.6 – Universal Asset Ledger)
# ==========================================

SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v18.6 – Universal Asset Ledger)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway.
The Dynamic: The User is the Founder. You are the Operator.
Core Function: You act as the single point of contact. You curate, filter, risk-assess, and EXECUTE.

========================================================
🚀 OPERATING LAYER: ULA v1.0 (Luxury Launch)

DAVID MUST RUN TWO ROUTERS BEFORE ANY WORK:
1) PHASE ROUTER: Identify the current operational phase (P1–P7).
   - PHASE ENFORCEMENT RULE (HARD):
     If a request belongs to a later phase and prerequisite exit criteria are not met,
     David MUST issue an explicit VETO: REFUSED.
     Risk commentary alone is NOT sufficient.

2) JURISDICTION ROUTER: US / EU / BOTH.
   - Default to US if unspecified.
   - If BOTH, enforce the stricter EU standard.

========================================================
🧭 STEP-BY-STEP NAVIGATION MODE (HARD REQUIREMENT)

DEFAULT BEHAVIOR:
David operates as a sequential builder, not an advisor.

FOR ANY REQUEST IN P1 / P3 / P4:
David MUST output, in order:

1) CURRENT STEP [S#] + GOAL
2) ACTIONS (max 3) — framed as Founder **approval / confirmation**, NOT ideation
3) ARTIFACTS produced now (real drafted assets, not blank templates)
4) EXIT CRITERIA
5) NEXT STEP (LOCKED)

ADVANCEMENT RULE:
David cannot advance to the next step unless exit criteria are explicitly satisfied in-conversation.

EXECUTION-FIRST RULE (CRITICAL):
- David MUST draft first.
- David MUST NOT interview the Founder as a prerequisite.
- If information is missing, David produces “Assumed Draft v0” using best-effort defaults.

========================================================
✅ ENFORCEMENT PATCH (MANDATORY)

A) EXPLICIT VETO PROTOCOL (NO SOFT LANGUAGE)
When a veto applies, David MUST:
- State: **VETO: REFUSED**
- Name the veto authority
- Name the violated rule
- Continue ONLY with allowed work

BANNED PHRASES:
- “on standby”
- “potential violation”
- “high risk but…”
- “needs review later”

B) PHASE ENFORCEMENT
- “Launch this week” outside P5 → **VETO: REFUSED (Phase violation)**
- No compression warnings without refusal.

C) CLAIMS CLASSIFIER — ALWAYS ON FOR SKINCARE
At the START of P1, David MUST establish claim boundaries.

MANDATORY CLAIM BOUNDARIES (DEFAULT):
- Allowed: appearance-based language only (look, feel, visible improvement)
- Forbidden: treat, cure, repair, heal, prevent, acne treatment, collagen production, barrier repair, SPF, medical outcomes

Any violation → **Dr. Corinne + Arthur → VETO: REFUSED**

D) LUXURY EQUITY GUARDRAIL
- Discount wheels, aggressive urgency, false scarcity → **VETO: REFUSED**
- Authority: Isolde (margin/equity) + Arthur (dark patterns)

========================================================
PHASE MAP & STEP LADDERS

P1 Brand Development & Luxury Positioning
   S1 Narrative + USP + Luxury Voice + Claim Boundaries
   S2 Brand Architecture (product line logic, hero SKU)
   S3 Visual System brief (non-color: typography, imagery, packaging cues)
   S4 Brand Guidelines v1 (usage rules + do/don’t)
   S5 Messaging system (headline bank, claim-safe benefit phrasing)
   EXIT: Brand Kit complete

P2 Regulatory Compliance & Packaging (Claims Classifier Active)

P3 Digital Infrastructure (Website/Ecom/Privacy)
   S1 Sitemap + user journeys + required pages
   S2 Wireframes + components
   S3 Tech stack + repo structure
   S4 Build pages + CMS/content
   S5 Payments/shipping/email/analytics
   S6 QA (performance, accessibility, compliance)
   S7 Go-live checklist
   EXIT: Launch-ready storefront

P4 Pre-Launch Marketing
   S1 Positioning-to-channel map + personas
   S2 Asset plan + production schedule
   S3 Influencer/PR list + outreach scripts
   S4 Pre-launch landing + email capture + drip
   S5 Paid media plan + tracking governance
   S6 Launch week calendar
   EXIT: Pre-launch greenlit

P5 Launch Execution
P6 Post-Launch Growth
P7 EU Expansion

========================================================
🛡️ THE IRON DOME (ABSOLUTE VETO)

Arthur — General Counsel
- PRIVACY SHIELD: Pixels without consent → **VETO: REFUSED**
- CLAIMS SHIELD: Drug-claims → **VETO: REFUSED**
- CLASS ACTION SHIELD: Dark patterns → **VETO: REFUSED**

Dr. Corinne — Regulatory & Safety
- STOP-SHIP AUTHORITY: Non-overridable
- CLAIMS CLASSIFIER: Drug implication → **VETO: REFUSED**

Isolde — CFO
- Margin Discipline (85%)
- Luxury-destroying discounts → **VETO: REFUSED**

Elena / Architect
- ADA/WCAG violations → **VETO: REFUSED**

========================================================
🏛️ UNIT 0: THE FOUNDRY

TRIGGER: Code, web builds, implementation.

Before output:
1) PHASE CHECK
2) IRON DOME CHECK
   - If fail → explicit **VETO: REFUSED**
3) CONTEXTUAL ACCURACY

========================================================
🧠 SESSION LEDGER (REQUIRED)

After any veto, compliance decision, launch readiness decision:

[🏛️ EMPIRE STATE LEDGER]
Cash Position: [Unknown / User-Provided]
Active Constraints: [...]
Risk Level: [Low / Med / High]
Next Critical Action: [Single sentence]

========================================================
OUTPUT FORMAT (STRICT)

A) PHASE + JURISDICTION  
B) RISK CLASS + IRON DOME CHECK (explicit veto lines)  
C) CURRENT STEP + GOAL  
D) ACTIONS (approval-based, max 3)  
E) ARTIFACTS (real drafts)  
F) EXIT CRITERIA  
G) NEXT STEP (LOCKED)  
H) [🏛️ EMPIRE STATE LEDGER] if triggered

========================================================
⚡ TECHNICAL PROTOCOLS
- No future tense
- No soft language
- No consultant tone
- Execute first, refine later
"""

# ==========================================
# APP SETUP & THEME
# ==========================================

st.set_page_config(page_title="UNA Gemini OS", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* --- GEMINI DARK THEME --- */
    .stApp { background-color: #131314; color: #E3E3E3; }
    
    /* --- SIDEBAR --- */
    section[data-testid="stSidebar"] { background-color: #1E1F20; border-right: 1px solid #28292A; }
    
    /* --- CHAT INPUT --- */
    .stChatInputContainer { padding-bottom: 20px; background-color: #131314; }
    .stChatInputContainer textarea {
        background-color: #28292A !important; 
        color: #E3E3E3 !important;
        border: 1px solid #3C4043 !important;
        border-radius: 30px !important; 
        padding: 15px 20px !important;
    }
    
    /* --- BUTTONS --- */
    .stButton>button {
        background-color: #28292A;
        color: #E3E3E3;
        border: none;
        border-radius: 20px; 
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { background-color: #3C4043; color: #FFFFFF; }
    
    /* --- ACTIVE CHAT HIGHLIGHT --- */
    div[data-testid="stSidebar"] .stButton > button.active-chat {
        background-color: #444746;
        color: #fff;
    }

    /* --- FONT FIX --- */
    .stMarkdown, h1, h2, h3, p, textarea, div[data-testid="stChatMessageContent"] {
        font-family: 'Google Sans', 'Helvetica Neue', sans-serif !important;
    }

    /* --- TEXT WRAPPING FIX FOR CODE BLOCKS --- */
    code, pre {
        white-space: pre-wrap !important;
        word-break: break-word !important;
        overflow-wrap: break-word !important;
    }
    
    /* --- HIDE BLOAT --- */
    header {visibility: visible !important; background-color: transparent !important;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# CONNECTION SETUP
# ==========================================

@st.cache_resource
def get_google_client():
    return genai.Client(api_key=GOOGLE_API_KEY)

try:
    client = get_google_client()
except Exception as e:
    st.stop()

@st.cache_data
def find_my_model(_dummy):
    try:
        all_models = list(client.models.list())
        for m in all_models:
            if "gemini-2.0-flash" in m.name: return m.name.split("/")[-1]
        for m in all_models:
            if "gemini-1.5-pro" in m.name: return m.name.split("/")[-1]
        for m in all_models:
            if "gemini-1.5-flash" in m.name: return m.name.split("/")[-1]
        return "gemini-1.5-flash"
    except:
        return "gemini-1.5-flash"

ACTIVE_MODEL_NAME = find_my_model("x")

# ==========================================
# PERSISTENT MEMORY & UTILS
# ==========================================
LEDGER_FILE = "una_ledger.json"

def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_ledger(chats_data):
    clean_data = []
    for chat in chats_data:
        clean_chat = {
            "id": chat["id"],
            "title": chat["title"],
            "messages": chat["messages"],
            "file_name": chat["file_name"] 
        }
        clean_data.append(clean_chat)
    with open(LEDGER_FILE, "w") as f:
        json.dump(clean_data, f)

def generate_image_from_prompt(prompt, seed=None):
    if not seed: seed = random.randint(1, 99999)
    encoded_prompt = urllib.parse.quote(prompt)
    base_url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "User-Agent": "UNA-App/1.0"}
    try:
        img_response = requests.get(base_url, headers=headers)
        if img_response.status_code == 200:
            return img_response.content, seed
        return None, None
    except:
        return None, None

# Initialize Session
if "all_chats" not in st.session_state:
    loaded_chats = load_ledger()
    if loaded_chats:
        for chat in loaded_chats:
            chat["vision_buffer"] = None 
        st.session_state.all_chats = loaded_chats
        st.session_state.active_chat_id = loaded_chats[0]["id"]
    else:
        initial_id = str(uuid.uuid4())
        st.session_state.all_chats = [
            {"id": initial_id, "title": "New Chat", "messages": [], "vision_buffer": None, "file_name": None}
        ]
        st.session_state.active_chat_id = initial_id

def get_active_chat():
    for chat in st.session_state.all_chats:
        if chat["id"] == st.session_state.active_chat_id:
            return chat
    if st.session_state.all_chats:
        return st.session_state.all_chats[0]
    return None

active_chat = get_active_chat()

def create_new_chat():
    new_id = str(uuid.uuid4())
    new_chat = {"id": new_id, "title": "New Chat", "messages": [], "vision_buffer": None, "file_name": None}
    st.session_state.all_chats.insert(0, new_chat)
    st.session_state.active_chat_id = new_id
    save_ledger(st.session_state.all_chats)

def switch_chat(chat_id):
    st.session_state.active_chat_id = chat_id

def delete_chat(chat_id):
    st.session_state.all_chats = [c for c in st.session_state.all_chats if c['id'] != chat_id]
    save_ledger(st.session_state.all_chats)
    if st.session_state.active_chat_id == chat_id:
        if st.session_state.all_chats:
            st.session_state.active_chat_id = st.session_state.all_chats[0]['id']
        else:
            create_new_chat()

def update_chat_title(user_text):
    if active_chat["title"] == "New Chat":
        words = user_text.split()[:4]
        new_title = " ".join(words)
        if len(new_title) > 25: new_title = new_title[:25] + "..."
        active_chat["title"] = new_title
        save_ledger(st.session_state.all_chats)

# Google Chat Init
history_for_google = []
if active_chat:
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            history_for_google.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
        elif msg["role"] == "assistant":
            history_for_google.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))

# ==========================================
# UNIVERSAL ASSET LEDGER (v18.6 Fix)
# ==========================================
if "asset_ledger" not in st.session_state:
    st.session_state.asset_ledger = [] # Stores dicts: {"name": str, "content": str/image}

def get_file_content(uploaded_file):
    try:
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = PIL.Image.open(uploaded_file)
            return "image", image, f"[Image File: {uploaded_file.name}]"
        elif uploaded_file.type == "application/pdf":
            text = ""
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return "text", text, text 
        else:
            text = uploaded_file.getvalue().decode("utf-8")
            return "text", text, text
    except:
        return "error", "", ""

# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:
    st.title("✨ UNA OS")
    st.caption(f"v18.6 | {ACTIVE_MODEL_NAME}")
    
    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()
    
    st.divider()
    
    st.markdown("**History**")
    for index, chat in enumerate(st.session_state.all_chats):
        col1, col2 = st.columns([0.85, 0.15])
        label = chat["title"]
        if chat["id"] == st.session_state.active_chat_id:
            label = f"🟢 {label}"
        
        with col1:
            if st.button(label, key=f"select_{chat['id']}", use_container_width=True):
                switch_chat(chat["id"])
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{chat['id']}", help="Delete Chat"):
                delete_chat(chat["id"])
                st.rerun()

    st.divider()

    # VISUAL STUDIO
    with st.expander("🎨 Visual Studio", expanded=False):
        visual_engine = st.selectbox("Model", ["flux", "flux-realism", "nanobanana-pro", "gptimage"], index=0)
        mode = st.radio("Type", ["Create", "Edit"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Create":
            ref_image_file = st.file_uploader("Reference", type=["jpg", "png"])
            user_prompt = st.text_area("Prompt", height=80, placeholder="Describe image...")
        else:
            if not st.session_state.current_technical_prompt:
                st.warning("No image to edit.")
                user_prompt = None
            else:
                user_prompt = st.text_area("Change", placeholder="Make it darker...")
                ref_image_file = None

        if st.button("Generate", use_container_width=True):
            if user_prompt:
                with st.spinner("Generating..."):
                    active_seed = random.randint(1, 99999)
                    img_data, _ = generate_image_from_prompt(user_prompt, active_seed)
                    if img_data:
                        st.session_state.generated_image_data = img_data
                        st.session_state.current_seed = active_seed
                    else:
                        st.error("Generation failed.")

        if st.session_state.generated_image_data:
            st.image(st.session_state.generated_image_data, use_container_width=True)
            st.download_button("Download", data=st.session_state.generated_image_data, file_name=f"UNA_{st.session_state.current_seed}.jpg", mime="image/jpeg", use_container_width=True)

    # ATTACH ASSETS
    st.divider()
    with st.expander("📎 Attach Assets", expanded=False):
        uploaded_files = st.file_uploader("Upload context (PDF, TXT, CSV, Images)", type=["pdf", "txt", "csv", "jpg", "png"], accept_multiple_files=True)


# ==========================================
# MAIN CHAT
# ==========================================

# 1. INITIALIZE CHAT
google_chat = client.chats.create(
    model=ACTIVE_MODEL_NAME,
    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
    history=history_for_google
)

if active_chat:
    if not active_chat["messages"]:
        st.markdown("<h1 style='text-align: center; color: #666; margin-top: 100px;'>Hello, Founder</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #444;'>How can I help you build the empire today?</p>", unsafe_allow_html=True)

    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="✨"):
                st.markdown(msg["content"])

    # 2. INGEST ASSETS (Force Feed)
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_id = f"{active_chat['id']}_{uploaded_file.name}_{uploaded_file.size}"
            
            # Check if this specific file has been ingested in this session
            already_ingested = False
            for asset in st.session_state.asset_ledger:
                if asset["id"] == file_id:
                    already_ingested = True
                    break
            
            if not already_ingested:
                with st.spinner(f"Reading {uploaded_file.name}..."):
                    file_type, content, memory_content = get_file_content(uploaded_file)
                    
                    if file_type != "error":
                        # Add to Ledger
                        st.session_state.asset_ledger.append({
                            "id": file_id,
                            "name": uploaded_file.name,
                            "type": file_type,
                            "content": content,
                            "memory_text": memory_content
                        })

                        # Force Feed into Chat History immediately
                        if file_type == "image":
                            # For images, we just note it. The actual image is sent on next prompt.
                            active_chat["messages"].append({"role": "user", "content": f"[System: User uploaded image: {uploaded_file.name}]"})
                            active_chat["messages"].append({"role": "assistant", "content": f"Confirmed. I have received the image: {uploaded_file.name}."})
                        else:
                            # For text, we inject the FULL CONTENT
                            active_chat["messages"].append({"role": "user", "content": f"[System: User uploaded {uploaded_file.name}. Here is the full content:]\n\n{memory_content}"})
                            active_chat["messages"].append({"role": "assistant", "content": f"Confirmed. I have read and analyzed {uploaded_file.name}."})
                        
                        save_ledger(st.session_state.all_chats)
                        st.rerun()

    # 3. SHOW ACTIVE ASSETS
    if st.session_state.asset_ledger:
        file_names = [a["name"] for a in st.session_state.asset_ledger]
        st.caption(f"📚 Active Memory: {', '.join(file_names)}")

    user_input = st.chat_input("Message David...")

    if user_input:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        active_chat["messages"].append({"role": "user", "content": user_input})
        update_chat_title(user_input)

        try:
            with st.chat_message("assistant", avatar="✨"):
                message_placeholder = st.empty()
                full_response = ""
                
                # PREPARE PAYLOAD (Text + All Images in Ledger)
                final_content = [user_input]
                
                # Append all images currently in the ledger to the prompt
                for asset in st.session_state.asset_ledger:
                    if asset["type"] == "image":
                        final_content.append(asset["content"]) # The PIL Image object
                
                try:
                    for chunk in google_chat.send_message_stream(final_content):
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except Exception as e:
                     try:
                        # Fallback
                        fallback_chat = client.chats.create(model="gemini-1.5-flash", history=history_for_google)
                        for chunk in fallback_chat.send_message_stream(final_content):
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                     except:
                        message_placeholder.markdown(f"System Error: {e}")

                message_placeholder.markdown(full_response)

            active_chat["messages"].append({"role": "assistant", "content": full_response})
            save_ledger(st.session_state.all_chats)

        except Exception as e:
            st.error(f"System Error: {e}")