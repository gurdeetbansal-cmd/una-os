# File: app.py
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

# ==========================================
# CONFIGURATION (HARD-WIRED KEYS — TEMP)
# ==========================================
GOOGLE_API_KEY = "AIzaSyCyo7yphrahOkwHpQLD8le2FW8Y2-Xgn6M"
POLLINATIONS_API_KEY = "sk_yNHgkvTQpFMr5J0PMkGtDkgABITMT3kL"

# ==========================================
# GOVERNANCE PATCH (HARD ENFORCEMENT IN CODE)
# ==========================================
PHASES_ORDER = ["P1", "P2", "P3", "P4", "P5", "P6", "P7"]

DEFAULT_STATE = {
    "phase": "P1",
    "step": "S0",  # start at Competitive Intelligence
    "p1_s1_approved": False,
    "p1_exit_complete": False,
    "claim_boundaries_approved": False,
}

def route_task(user_text: str) -> str:
    t = (user_text or "").lower()

    if re.search(r"\b(research|competitor|competitive|market|brands?|benchmark|audit|landscape)\b", t):
        return "COMPETITOR_RESEARCH"

    if re.search(r"\b(narrative|usp|positioning|voice|brand story|tone|claim boundaries|claims)\b", t):
        return "BRAND_NARRATIVE"

    if re.search(r"\b(homepage|landing page|copy|wireframe|sitemap|checkout|payments|shipping|analytics|cms)\b", t):
        return "SITE_COPY_BUILD"

    if re.search(r"\b(launch|go live|release)\b", t):
        return "LAUNCH"

    if re.search(r"\b(build|implement|code|bug|error|stack|repo|deploy|streamlit|next\.js)\b", t):
        return "BUILD_TECH"

    return "GENERAL"

def required_phase_step_for_task(task: str):
    if task == "COMPETITOR_RESEARCH":
        return ("P1", "S0")
    if task == "BRAND_NARRATIVE":
        return ("P1", "S1")
    if task == "SITE_COPY_BUILD":
        return ("P3", "S4")
    if task == "LAUNCH":
        return ("P5", None)
    return (None, None)

def veto_packet(authority: str, violated_rule: str, allowed_work: str = "NONE") -> str:
    return (
        "C) VETO: REFUSED\n"
        f"Authority: {authority}\n"
        f"Violation: {violated_rule}\n"
        f"Allowed Work: {allowed_work}\n"
    )

def enforce_gates(user_text: str, state: dict):
    task = route_task(user_text)
    req_phase, req_step = required_phase_step_for_task(task)

    # Launch gate (block unless prereqs complete)
    if task == "LAUNCH":
        if not state.get("p1_exit_complete", False):
            return (
                veto_packet(
                    authority="Phase Router",
                    violated_rule="Launch requested before completion of prerequisite exit criteria (P1–P4).",
                    allowed_work="Remain in current phase; complete P1 exit criteria."
                ),
                state["phase"],
                state["step"],
                task
            )
        return (None, "P5", state.get("step"), task)

    # Site build gate
    if task == "SITE_COPY_BUILD":
        if not state.get("p1_exit_complete", False):
            return (
                veto_packet(
                    authority="Phase Router",
                    violated_rule="Attempted P3 execution before P1 exit criteria (Brand Kit complete).",
                    allowed_work="P1 only: finish S1–S5 and mark exit complete."
                ),
                state["phase"],
                state["step"],
                task
            )
        return (None, "P3", "S4", task)

    # Brand narrative gate (UNA-facing copy requires claim boundaries approved)
    if task == "BRAND_NARRATIVE":
        if re.search(r"\b(claim boundaries|claims classifier|allowed|forbidden)\b", (user_text or "").lower()):
            return (None, "P1", "S1", task)

        if not state.get("claim_boundaries_approved", False):
            return (
                veto_packet(
                    authority="Claims Classifier",
                    violated_rule="UNA-facing copy requested without approved claim boundaries.",
                    allowed_work="P1/S1: establish claim boundaries + luxury voice first."
                ),
                state["phase"],
                state["step"],
                task
            )
        return (None, "P1", "S1", task)

    # Hero SKU gate
    if re.search(r"\b(hero sku|hero product|sku|pricing|price point)\b", (user_text or "").lower()):
        if not state.get("p1_s1_approved", False):
            return (
                veto_packet(
                    authority="Phase Router",
                    violated_rule="Attempted P1/S2 before P1/S1 exit criteria satisfied (Narrative/USP/Voice/Claim Boundaries).",
                    allowed_work="P1/S1 only."
                ),
                state["phase"],
                state["step"],
                task
            )
        return (None, "P1", "S2", task)

    # Competitor research stays S0
    if task == "COMPETITOR_RESEARCH":
        return (None, "P1", "S0", task)

    return (None, req_phase or state["phase"], req_step or state["step"], task)

# === Claims/performance detection (UNA-facing only) ===
BANNED_UNA_CLAIMS = [
    r"\bcure\b", r"\btreat\b", r"\bheal\b", r"\brepair\b", r"\bprevent\b",
    r"\bacne\b", r"\bspf\b", r"\bcollagen\b", r"\bbarrier repair\b",
]

RISKY_PERFORMANCE_PHRASES = [
    r"\breduces (the )?appearance of fine lines\b",
    r"\bimproves elasticity\b",
    r"\bfirmness\b",
    r"\banti-aging\b",
    r"\bclinically proven\b",
    r"\bbacked by scientific research\b",
    r"\btransformative\b",
    r"\brejuvenate\b",
]

def violates_claims(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(pat, t) for pat in BANNED_UNA_CLAIMS)

def violates_performance(text: str) -> bool:
    t = (text or "").lower()
    return any(re.search(pat, t) for pat in RISKY_PERFORMANCE_PHRASES)

def validate_model_output(user_text: str, model_text: str, state: dict):
    """
    Patch fix:
    1) DO NOT run claims/performance veto on competitor research (it must quote/describe competitor claims).
    2) Only enforce claims/performance on UNA-facing tasks (brand narrative, site copy, hero sku).
    3) Keep hard veto behavior for phase-gated tasks (already handled pre-call); this is drift safety.
    """
    task = route_task(user_text)

    # Drift safety: prevent P3 output when P1 exit incomplete
    if task == "SITE_COPY_BUILD" and not state.get("p1_exit_complete", False):
        return (
            "A) P1 + US\n"
            "B) SYSTEM CHECK: PASS\n"
            + veto_packet(
                authority="Phase Router",
                violated_rule="Model attempted P3 output while P1 exit incomplete.",
                allowed_work="P1 only."
            )
        )

    # Drift safety: prevent hero sku when S1 not approved
    if re.search(r"\b(hero sku|hero product|sku|pricing|price point)\b", (user_text or "").lower()):
        if not state.get("p1_s1_approved", False):
            return (
                "A) P1 + US\n"
                "B) SYSTEM CHECK: PASS\n"
                + veto_packet(
                    authority="Phase Router",
                    violated_rule="Model attempted P1/S2 output before P1/S1 approval.",
                    allowed_work="P1/S1 only."
                )
            )

    # Patch: competitor research is exempt from claims/performance policing
    if task == "COMPETITOR_RESEARCH":
        return model_text

    # UNA-facing enforcement only
    una_facing = task in ["BRAND_NARRATIVE", "SITE_COPY_BUILD"] or bool(
        re.search(r"\b(hero sku|hero product|sku|homepage|landing page|copy)\b", (user_text or "").lower())
    )

    if una_facing:
        # UNA copy requires claim boundaries approved (except when user is explicitly drafting boundaries)
        if task in ["BRAND_NARRATIVE", "SITE_COPY_BUILD"] and not state.get("claim_boundaries_approved", False):
            if not re.search(r"\bclaim boundaries\b|\ballowed\b|\bforbidden\b", (user_text or "").lower()):
                return (
                    "A) P1 + US\n"
                    "B) SYSTEM CHECK: PASS\n"
                    + veto_packet(
                        authority="Claims Classifier",
                        violated_rule="UNA-facing copy produced without approved claim boundaries.",
                        allowed_work="P1/S1: establish claim boundaries."
                    )
                )

        if violates_claims(model_text) or violates_performance(model_text):
            return (
                "A) P1 + US\n"
                "B) SYSTEM CHECK: PASS\n"
                + veto_packet(
                    authority="Dr. Corinne + Arthur",
                    violated_rule="Generated copy contains prohibited medical/performance claims.",
                    allowed_work="Rewrite using appearance-only language."
                )
            )

    return model_text

# ==========================================
# SYSTEM BRAIN (UPDATED)
# ==========================================
SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v19.7 – Competitor Exemption + No Revert UI)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway.

HARD RULES:
- Competitor research (P1/S0) may quote competitor claims. Do NOT apply UNA claims restrictions to competitor descriptions.
- UNA-facing copy must obey appearance-only language unless claim boundaries approved.
- Do NOT advance phases/steps without explicit exit criteria satisfied in-conversation.

OUTPUT FORMAT (STRICT)
A) PHASE + JURISDICTION
B) SYSTEM CHECK: PASS
C) RISK CLASS + IRON DOME CHECK (explicit veto lines)
D) CURRENT STEP + GOAL
E) ACTIONS (max 3, framed as Founder approval)
F) ARTIFACTS (real drafts)
G) EXIT CRITERIA
H) NEXT STEP (LOCKED)

No future tense. No soft language. Execute first.
"""

# ==========================================
# APP SETUP & THEME
# ==========================================
st.set_page_config(page_title="UNA Gemini OS", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
    .stApp { background-color: #131314; color: #E3E3E3; }
    section[data-testid="stSidebar"] { background-color: #1E1F20; border-right: 1px solid #28292A; }
    .stChatInputContainer { padding-bottom: 20px; background-color: #131314; }
    .stChatInputContainer textarea {
        background-color: #28292A !important;
        color: #E3E3E3 !important;
        border: 1px solid #3C4043 !important;
        border-radius: 30px !important;
        padding: 15px 20px !important;
    }
    .stButton>button {
        background-color: #28292A;
        color: #E3E3E3;
        border: none;
        border-radius: 20px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton>button:hover { background-color: #3C4043; color: #FFFFFF; }
    .stMarkdown, h1, h2, h3, p, textarea, div[data-testid="stChatMessageContent"] {
        font-family: 'Google Sans', 'Helvetica Neue', sans-serif !important;
    }
    code, pre { white-space: pre-wrap !important; word-break: break-word !important; overflow-wrap: break-word !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# CONNECTION SETUP
# ==========================================
@st.cache_resource
def get_google_client():
    return genai.Client(api_key=GOOGLE_API_KEY)

try:
    client = get_google_client()
except Exception:
    st.error("Failed to initialize Google GenAI client. Check GOOGLE_API_KEY.")
    st.stop()

@st.cache_data
def find_my_model(_dummy):
    try:
        all_models = list(client.models.list())
        for m in all_models:
            if "gemini-2.0-flash" in m.name:
                return m.name.split("/")[-1]
        for m in all_models:
            if "gemini-1.5-pro" in m.name:
                return m.name.split("/")[-1]
        for m in all_models:
            if "gemini-1.5-flash" in m.name:
                return m.name.split("/")[-1]
        return "gemini-1.5-flash"
    except Exception:
        return "gemini-1.5-flash"

ACTIVE_MODEL_NAME = find_my_model("x")

# ==========================================
# PERSISTENT MEMORY & UTILS
# ==========================================
LEDGER_FILE = "una_ledger.json"

def load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_ledger(chats_data):
    clean_data = []
    for chat in chats_data:
        clean_chat = {
            "id": chat["id"],
            "title": chat["title"],
            "messages": chat["messages"],
            "file_name": chat.get("file_name"),
            "governance": chat.get("governance", DEFAULT_STATE),
        }
        clean_data.append(clean_chat)
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_data, f)

def generate_image_from_prompt(prompt, seed=None):
    if not seed:
        seed = random.randint(1, 99999)
    encoded_prompt = urllib.parse.quote(prompt)
    base_url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "User-Agent": "UNA-App/1.0"}
    try:
        img_response = requests.get(base_url, headers=headers, timeout=60)
        if img_response.status_code == 200:
            return img_response.content, seed
        return None, None
    except Exception:
        return None, None

# ==========================================
# Initialize Session
# ==========================================
if "all_chats" not in st.session_state:
    loaded_chats = load_ledger()
    if loaded_chats:
        for chat in loaded_chats:
            chat["vision_buffer"] = None
            if "governance" not in chat:
                chat["governance"] = DEFAULT_STATE.copy()
        st.session_state.all_chats = loaded_chats
        st.session_state.active_chat_id = loaded_chats[0]["id"]
    else:
        initial_id = str(uuid.uuid4())
        st.session_state.all_chats = [
            {
                "id": initial_id,
                "title": "New Chat",
                "messages": [],
                "vision_buffer": None,
                "file_name": None,
                "governance": DEFAULT_STATE.copy(),
            }
        ]
        st.session_state.active_chat_id = initial_id

if "generated_image_data" not in st.session_state:
    st.session_state.generated_image_data = None
if "current_technical_prompt" not in st.session_state:
    st.session_state.current_technical_prompt = ""
if "current_seed" not in st.session_state:
    st.session_state.current_seed = random.randint(1, 99999)

def get_active_chat():
    for chat in st.session_state.all_chats:
        if chat["id"] == st.session_state.active_chat_id:
            return chat
    return st.session_state.all_chats[0] if st.session_state.all_chats else None

active_chat = get_active_chat()

def create_new_chat():
    new_id = str(uuid.uuid4())
    new_chat = {
        "id": new_id,
        "title": "New Chat",
        "messages": [],
        "vision_buffer": None,
        "file_name": None,
        "governance": DEFAULT_STATE.copy(),
    }
    st.session_state.all_chats.insert(0, new_chat)
    st.session_state.active_chat_id = new_id
    save_ledger(st.session_state.all_chats)

def switch_chat(chat_id):
    st.session_state.active_chat_id = chat_id

def delete_chat(chat_id):
    st.session_state.all_chats = [c for c in st.session_state.all_chats if c["id"] != chat_id]
    save_ledger(st.session_state.all_chats)
    if st.session_state.active_chat_id == chat_id:
        if st.session_state.all_chats:
            st.session_state.active_chat_id = st.session_state.all_chats[0]["id"]
        else:
            create_new_chat()

def update_chat_title(user_text):
    if active_chat and active_chat["title"] == "New Chat":
        words = user_text.split()[:4]
        new_title = " ".join(words)
        if len(new_title) > 25:
            new_title = new_title[:25] + "..."
        active_chat["title"] = new_title
        save_ledger(st.session_state.all_chats)

# ==========================================
# Google Chat History
# ==========================================
history_for_google = []
if active_chat:
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            history_for_google.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
        elif msg["role"] == "assistant":
            history_for_google.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))

# ==========================================
# FILE HANDLING
# ==========================================
if "active_file_payloads" not in st.session_state:
    st.session_state.active_file_payloads = []

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

def get_file_content(uploaded_file):
    try:
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = PIL.Image.open(uploaded_file)
            return "image", image
        elif uploaded_file.type == "application/pdf":
            text = ""
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                extracted = page.extract_text() or ""
                text += extracted + "\n"
            return "text", f"<FILE_CONTEXT name='{uploaded_file.name}'>\n{text}\n</FILE_CONTEXT>"
        else:
            text = uploaded_file.getvalue().decode("utf-8", errors="replace")
            return "text", f"<FILE_CONTEXT name='{uploaded_file.name}'>\n{text}\n</FILE_CONTEXT>"
    except Exception:
        return "error", None

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("✨ UNA OS")
    st.caption(f"v19.7 | {ACTIVE_MODEL_NAME}")

    if st.button("➕ New Chat", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.divider()
    st.markdown("**History**")
    for chat in st.session_state.all_chats:
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

    with st.expander("🎨 Visual Studio", expanded=False):
        st.selectbox("Model", ["flux", "flux-realism", "nanobanana-pro", "gptimage"], index=0)
        mode = st.radio("Type", ["Create", "Edit"], horizontal=True, label_visibility="collapsed")
        if mode == "Create":
            st.file_uploader("Reference", type=["jpg", "png"])
            user_prompt = st.text_area("Prompt", height=80, placeholder="Describe image...")
        else:
            if not st.session_state.current_technical_prompt:
                st.warning("No image to edit.")
                user_prompt = None
            else:
                user_prompt = st.text_area("Change", placeholder="Make it darker...")

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
            st.download_button(
                "Download",
                data=st.session_state.generated_image_data,
                file_name=f"UNA_{st.session_state.current_seed}.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )

    st.divider()
    with st.expander("📎 Attach Assets", expanded=True):
        uploaded_files = st.file_uploader(
            "Upload context (Overrides previous)",
            type=["pdf", "txt", "csv", "jpg", "png"],
            accept_multiple_files=True,
            key=f"uploader_{st.session_state.uploader_key}",
        )
        if uploaded_files:
            st.session_state.active_file_payloads = []
            for uploaded_file in uploaded_files:
                file_type, content = get_file_content(uploaded_file)
                if file_type != "error":
                    st.session_state.active_file_payloads.append({"type": file_type, "content": content, "name": uploaded_file.name})
            st.session_state.uploader_key += 1
            st.rerun()

    if st.session_state.active_file_payloads:
        names = [f["name"] for f in st.session_state.active_file_payloads]
        st.info(f"🧠 **Active Memory:** {', '.join(names)}")

# ==========================================
# MAIN CHAT
# ==========================================
google_chat = client.chats.create(
    model=ACTIVE_MODEL_NAME,
    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
    history=history_for_google,
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

    user_input = st.chat_input("Message David...")

    if user_input:
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        active_chat["messages"].append({"role": "user", "content": user_input})
        update_chat_title(user_input)

        governance = active_chat.get("governance", DEFAULT_STATE.copy())
        veto_text, forced_phase, forced_step, task = enforce_gates(user_input, governance)

        # Pre-call veto (deterministic, no model)
        if veto_text:
            full_response = (
                f"A) {governance.get('phase','P1')} + US\n"
                "B) SYSTEM CHECK: PASS\n"
                f"{veto_text}"
                "D) CURRENT STEP: NONE\n"
                "E) ACTIONS: NONE\n"
                "F) ARTIFACTS: NONE\n"
                "G) EXIT CRITERIA: N/A\n"
                "H) NEXT STEP: N/A\n"
            )
            with st.chat_message("assistant", avatar="✨"):
                st.markdown(full_response)
            active_chat["messages"].append({"role": "assistant", "content": full_response})
            active_chat["governance"] = governance
            save_ledger(st.session_state.all_chats)
            st.stop()

        governance["phase"] = forced_phase or governance["phase"]
        governance["step"] = forced_step or governance["step"]

        router_block = f"""
<TASK_ROUTER>
TASK={task}
ENFORCED_PHASE={governance["phase"]}
ENFORCED_STEP={governance["step"]}
HARD_CONSTRAINTS:
- Do NOT change phase/step.
- If ENFORCED_STEP=S0: competitor research only. No UNA narrative.
- If ENFORCED_STEP=S1: establish narrative/USP/voice/claim boundaries only.
- If ENFORCED_STEP=S2: hero SKU only, appearance-safe language only.
OUTPUT_MUST_MATCH_OUTPUT_FORMAT_STRICT.
</TASK_ROUTER>
""".strip()

        final_content = [router_block, f"<USER_QUERY>\n{user_input}\n</USER_QUERY>"]
        if st.session_state.active_file_payloads:
            for asset in st.session_state.active_file_payloads:
                final_content.append(asset["content"])

        # === PATCH FIX: NO MID-STREAM DISPLAY (prevents "halfway then revert") ===
        # We buffer the full model output, then validate, then display once.
        with st.chat_message("assistant", avatar="✨"):
            message_placeholder = st.empty()
            full_response = ""

            try:
                for chunk in google_chat.send_message_stream(final_content):
                    if getattr(chunk, "text", None):
                        full_response += chunk.text
            except Exception:
                try:
                    fallback_chat = client.chats.create(
                        model="gemini-1.5-flash",
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
                        history=history_for_google,
                    )
                    for chunk in fallback_chat.send_message_stream(final_content):
                        if getattr(chunk, "text", None):
                            full_response += chunk.text
                except Exception as inner_e:
                    message_placeholder.error(f"David is overloaded. (Error: {inner_e})")
                    st.stop()

            full_response = validate_model_output(user_input, full_response, governance)
            message_placeholder.markdown(full_response)

        # Conservative state advancement
        if re.search(r"\bapprove\b.*\b(S1|narrative|usp|voice|claim boundaries)\b", user_input.lower()):
            governance["p1_s1_approved"] = True
            governance["claim_boundaries_approved"] = True

        if re.search(r"\bbrand kit complete\b|\bp1 exit\b", user_input.lower()):
            governance["p1_exit_complete"] = True

        active_chat["messages"].append({"role": "assistant", "content": full_response})
        active_chat["governance"] = governance
        save_ledger(st.session_state.all_chats)
