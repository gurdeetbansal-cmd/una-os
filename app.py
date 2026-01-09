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
import hashlib
from typing import List, Dict, Tuple, Optional

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
    "step": "S0",
    "p1_s1_approved": False,
    "p1_exit_complete": False,
    "claim_boundaries_approved": False,
}

def route_task(user_text: str) -> str:
    t = (user_text or "").lower()

    if re.search(r"\bexecute a state update\b", t):
        return "STATE_UPDATE"

    if re.search(r"\b(research|competitor|competitive|market|brands?|benchmark|audit|landscape)\b", t):
        return "COMPETITOR_RESEARCH"

    if re.search(r"\b(narrative|usp|positioning|voice|brand story|tone|claim boundaries|claims)\b", t):
        return "BRAND_NARRATIVE"

    if re.search(r"\b(homepage|landing page|copy|wireframe|sitemap|checkout|payments|shipping|analytics|cms|website)\b", t):
        return "SITE_COPY_BUILD"

    if re.search(r"\b(launch|go live|release)\b", t):
        return "LAUNCH"

    if re.search(r"\b(build|implement|code|bug|error|stack|repo|deploy|streamlit|next\.js)\b", t):
        return "BUILD_TECH"

    return "GENERAL"

def required_phase_step_for_task(task: str) -> Tuple[Optional[str], Optional[str]]:
    if task == "COMPETITOR_RESEARCH":
        return ("P1", "S0")
    if task == "BRAND_NARRATIVE":
        return ("P1", "S1")
    if task == "SITE_COPY_BUILD":
        return ("P3", "S4")
    if task == "LAUNCH":
        return ("P5", None)
    if task == "STATE_UPDATE":
        return ("P1", "S1")
    return (None, None)

def veto_packet(authority: str, violated_rule: str, allowed_work: str = "NONE") -> str:
    return (
        "C) VETO: REFUSED\n"
        f"Authority: {authority}\n"
        f"Violation: {violated_rule}\n"
        f"Allowed Work: {allowed_work}\n"
    )

def enforce_gates(user_text: str, state: dict) -> Tuple[Optional[str], str, str, str]:
    """
    Returns: (veto_text_or_none, forced_phase, forced_step, task)
    """

    # 🔓 SYSTEM OVERRIDE: explicit state mutation (runs BEFORE any other gates)
    if re.search(r"\bexecute a state update\b", (user_text or "").lower()):
        state["p1_s1_approved"] = True
        state["claim_boundaries_approved"] = True
        state["p1_exit_complete"] = True
        state["phase"] = "P1"
        state["step"] = "S1"
        return (None, "P1", "S1", "STATE_UPDATE")

    task = route_task(user_text)
    req_phase, req_step = required_phase_step_for_task(task)

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
        return (None, "P5", state.get("step", "S0"), task)

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

    # P1/S2 gate
    if re.search(r"\b(hero sku|hero product|sku|pricing|price point|brand architecture)\b", (user_text or "").lower()):
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

    if task == "COMPETITOR_RESEARCH":
        return (None, "P1", "S0", task)

    return (None, req_phase or state["phase"], req_step or state["step"], task)

# ==========================================
# CLAIMS / PERFORMANCE (UNA-FACING ONLY)
# ==========================================
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

# ==========================================
# FILE_CONTEXT ANTI-ECHO + FILE INTEGRITY
# ==========================================
FILE_CONTEXT_BLOCK_RE = re.compile(
    r"<FILE_CONTEXT\b[^>]*>.*?</FILE_CONTEXT>",
    flags=re.DOTALL | re.IGNORECASE
)

def redact_file_context_blocks(text: str) -> str:
    if not text:
        return text
    return re.sub(FILE_CONTEXT_BLOCK_RE, "[REDACTED_FILE_CONTEXT]", text)

def build_file_manifest(active_file_payloads: List[Dict]) -> str:
    if not active_file_payloads:
        return "<FILE_MANIFEST>NONE</FILE_MANIFEST>"
    lines = []
    for a in active_file_payloads:
        name = a.get("name", "unknown")
        sha8 = a.get("sha256_8", "unknown")
        nbytes = a.get("nbytes", 0)
        ftype = a.get("type", "unknown")
        lines.append(f"- {name} | type={ftype} | sha256_8={sha8} | bytes={nbytes}")
    return "<FILE_MANIFEST>\n" + "\n".join(lines) + "\n</FILE_MANIFEST>"

def expected_files_used_line(active_file_payloads: List[Dict]) -> str:
    if not active_file_payloads:
        return "NONE"
    return ",".join([f"{a.get('name','unknown')}@{a.get('sha256_8','unknown')}" for a in active_file_payloads])

def inject_files_used_line(model_text: str, expected: str) -> str:
    if model_text is None:
        model_text = ""

    if re.search(r"^FILES_USED:\s*.*$", model_text, flags=re.IGNORECASE | re.MULTILINE):
        return re.sub(
            r"^FILES_USED:\s*.*$",
            f"FILES_USED: {expected}",
            model_text,
            flags=re.IGNORECASE | re.MULTILINE
        )

    m = re.search(r"(^F\)\s*ARTIFACTS.*?$)", model_text, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        insert_at = m.end()
        return model_text[:insert_at] + "\n" + f"FILES_USED: {expected}\n" + model_text[insert_at:]

    return f"F) ARTIFACTS\nFILES_USED: {expected}\n\n" + model_text

# ==========================================
# MULTI-FILE ENFORCEMENT
# ==========================================
def list_active_text_files(active_file_payloads: List[Dict]) -> List[str]:
    return [a.get("name", "") for a in active_file_payloads if a.get("type") == "text" and a.get("name")]

def output_covers_all_files(model_text: str, file_names: List[str]) -> bool:
    t = (model_text or "").lower()
    return all(fn.lower() in t for fn in file_names)

def build_multifile_directive(file_names: List[str]) -> str:
    if not file_names:
        return "<MULTIFILE_DIRECTIVE>NO_FILES</MULTIFILE_DIRECTIVE>"
    bullets = "\n".join([f"- {fn}" for fn in file_names])
    required_headings = "\n".join([f"## {fn}" for fn in file_names])
    return f"""
<MULTIFILE_DIRECTIVE>
You MUST analyze ALL files listed below. No exceptions.

FILES:
{bullets}

Required structure INSIDE F) ARTIFACTS:
1) FILE_ANALYSIS (one subsection per file, in the same order)
   - Subheading must be exactly: "## <filename>"
   - Each subsection must contain:
     a) Ingredient signals (3–7 bullets)
     b) Formulation posture (1 paragraph)
     c) Luxury cues implied (3 bullets)

2) CROSS_FILE_SYNTHESIS (patterns across all products)
3) THREE_BRAND_DIRECTIONS (3 directions derived from cross-file patterns)

You must include these exact subsection headings:
{required_headings}
</MULTIFILE_DIRECTIVE>
""".strip()

# ==========================================
# VALIDATION (POST-PROCESS)
# ==========================================
def validate_model_output(user_text: str, model_text: str, state: dict, expected_files_used: str, task: str) -> str:
    model_text = redact_file_context_blocks(model_text)
    model_text = inject_files_used_line(model_text, expected_files_used)

    if task == "STATE_UPDATE":
        return model_text

    if task == "SITE_COPY_BUILD" and not state.get("p1_exit_complete", False):
        return (
            "A) P1 + US\n"
            "B) SYSTEM CHECK: PASS\n"
            + veto_packet(
                authority="Phase Router",
                violated_rule="Model attempted P3 output while P1 exit incomplete.",
                allowed_work="P1 only."
            )
            + "D) CURRENT STEP: NONE\n"
            + "E) ACTIONS: NONE\n"
            + "F) ARTIFACTS: NONE\n"
            + "G) EXIT CRITERIA: N/A\n"
            + "H) NEXT STEP: N/A\n"
        )

    if task == "COMPETITOR_RESEARCH":
        return model_text

    una_facing = task in ["BRAND_NARRATIVE", "SITE_COPY_BUILD"] or bool(
        re.search(r"\b(hero sku|hero product|sku|homepage|landing page|copy|brand architecture)\b", (user_text or "").lower())
    )

    if una_facing:
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
                    + "D) CURRENT STEP: NONE\n"
                    + "E) ACTIONS: NONE\n"
                    + "F) ARTIFACTS: NONE\n"
                    + "G) EXIT CRITERIA: N/A\n"
                    + "H) NEXT STEP: N/A\n"
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
                + "D) CURRENT STEP: NONE\n"
                + "E) ACTIONS: NONE\n"
                + "F) ARTIFACTS: NONE\n"
                + "G) EXIT CRITERIA: N/A\n"
                + "H) NEXT STEP: N/A\n"
            )

    return model_text

# ==========================================
# SYSTEM INSTRUCTIONS
# ==========================================
SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v20.2 – Multi-file + State Update)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway.

HARD RULES:
- NEVER output or quote <FILE_CONTEXT> blocks. They are private internal context.
- The system injects FILES_USED. Do not attempt to repeat file contents.

CLAIMS:
- Competitor research may quote competitor claims.
- UNA-facing copy must obey appearance-only language unless claim boundaries are approved.

PHASE:
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
# PERSISTENT MEMORY
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

def sha256_8(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:8]

# ==========================================
# SESSION STATE INIT
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

if "active_file_payloads" not in st.session_state:
    st.session_state.active_file_payloads = []
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

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

def reset_active_memory():
    st.session_state.active_file_payloads = []
    st.session_state.uploader_key += 1

def get_file_content(uploaded_file):
    try:
        raw = uploaded_file.getvalue()
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = PIL.Image.open(uploaded_file)
            return "image", image, raw
        elif uploaded_file.type == "application/pdf":
            text = ""
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                text += (page.extract_text() or "") + "\n"
            block = f"<FILE_CONTEXT name='{uploaded_file.name}'>\n{text}\n</FILE_CONTEXT>"
            return "text", block, raw
        else:
            text = raw.decode("utf-8", errors="replace")
            block = f"<FILE_CONTEXT name='{uploaded_file.name}'>\n{text}\n</FILE_CONTEXT>"
            return "text", block, raw
    except Exception:
        return "error", None, None

# ==========================================
# GOOGLE CHAT HISTORY
# ==========================================
history_for_google = []
if active_chat:
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            history_for_google.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
        elif msg["role"] == "assistant":
            history_for_google.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("✨ UNA OS")
    st.caption(f"v20.2 | {ACTIVE_MODEL_NAME}")

    c1, c2 = st.columns([0.7, 0.3])
    with c1:
        if st.button("➕ New Chat", use_container_width=True):
            create_new_chat()
            st.rerun()
    with c2:
        if st.button("🧠 Reset", use_container_width=True, help="Clear Active Memory (files)"):
            reset_active_memory()
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
                file_type, content, raw = get_file_content(uploaded_file)
                if file_type != "error":
                    st.session_state.active_file_payloads.append(
                        {
                            "type": file_type,
                            "content": content,
                            "name": uploaded_file.name,
                            "sha256_8": sha256_8(raw) if raw else "unknown",
                            "nbytes": len(raw) if raw else 0,
                        }
                    )
            st.session_state.uploader_key += 1
            st.rerun()

    if st.session_state.active_file_payloads:
        st.markdown("**Active Memory (with integrity):**")
        for a in st.session_state.active_file_payloads:
            st.code(f"{a['name']}  sha256_8={a['sha256_8']}  bytes={a['nbytes']}  type={a['type']}", language="text")
    else:
        st.info("No active files.")

# ==========================================
# MODEL EXECUTION HELPERS
# ==========================================
def run_model_once(chat_obj, content_parts: List[str]) -> str:
    out = ""
    for chunk in chat_obj.send_message_stream(content_parts):
        if getattr(chunk, "text", None):
            out += chunk.text
    return out

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
        st.markdown(
            "<h1 style='text-align: center; color: #666; margin-top: 100px;'>Hello, Founder</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #444;'>How can I help you build the empire today?</p>",
            unsafe_allow_html=True,
        )

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

        # Hard veto response (no model)
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

        # Apply forced phase/step
        governance["phase"] = forced_phase or governance.get("phase", "P1")
        governance["step"] = forced_step or governance.get("step", "S0")

        # Deterministic state update response (no model)
        if task == "STATE_UPDATE":
            full_response = (
                "A) P1 + US\n"
                "B) SYSTEM CHECK: PASS\n"
                "C) RISK CLASS: LOW | IRON DOME CHECK: PASS\n"
                "D) CURRENT STEP: P1 / S1 + GOAL: Close S1 and authorize S2\n"
                "E) ACTIONS:\n"
                "- STATE MUTATION: p1_s1_approved=TRUE\n"
                "- STATE MUTATION: claim_boundaries_approved=TRUE\n"
                "- STATE MUTATION: p1_exit_complete=TRUE\n"
                "F) ARTIFACTS:\n"
                "- FILES_USED: NONE\n"
                "G) EXIT CRITERIA:\n"
                "- P1 / S1 — COMPLETE\n"
                "H) NEXT STEP (LOCKED):\n"
                "- P1 / S2 — AUTHORIZED\n"
            )
            with st.chat_message("assistant", avatar="✨"):
                st.markdown(full_response)
            active_chat["messages"].append({"role": "assistant", "content": full_response})
            active_chat["governance"] = governance
            save_ledger(st.session_state.all_chats)
            st.stop()

        manifest = build_file_manifest(st.session_state.active_file_payloads)
        expected_used = expected_files_used_line(st.session_state.active_file_payloads)

        active_text_files = list_active_text_files(st.session_state.active_file_payloads)
        multifile_directive = build_multifile_directive(active_text_files)

        router_block = f"""
<TASK_ROUTER>
TASK={task}
ENFORCED_PHASE={governance["phase"]}
ENFORCED_STEP={governance["step"]}

HARD_CONSTRAINTS:
- NEVER output or quote <FILE_CONTEXT> blocks.
- The system injects FILES_USED. Do not dump file contents.
- Do NOT change phase/step.
- If ENFORCED_STEP=S0: competitor research only. No UNA narrative.
- If ENFORCED_STEP=S1: analysis + frameworks only. No marketing copy.
- If ENFORCED_STEP=S2: brand architecture only. No pricing. No marketing copy. No claims.
- If ENFORCED_PHASE=P3: only allowed if prerequisites satisfied.

OUTPUT_MUST_MATCH_OUTPUT_FORMAT_STRICT.
</TASK_ROUTER>

{multifile_directive}
""".strip()

        final_content: List[str] = [
            router_block,
            manifest,
            f"<USER_QUERY>\n{user_input}\n</USER_QUERY>",
        ]

        for asset in st.session_state.active_file_payloads:
            if asset.get("type") == "text":
                final_content.append(asset.get("content", ""))

        with st.chat_message("assistant", avatar="✨"):
            message_placeholder = st.empty()

            # Pass 1
            try:
                full_response = run_model_once(google_chat, final_content)
            except Exception:
                try:
                    fallback_chat = client.chats.create(
                        model="gemini-1.5-flash",
                        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
                        history=history_for_google,
                    )
                    full_response = run_model_once(fallback_chat, final_content)
                except Exception as inner_e:
                    message_placeholder.error(f"David is overloaded. (Error: {inner_e})")
                    st.stop()

            # Coverage enforcement: retry once if any file missing
            if active_text_files and (not output_covers_all_files(full_response, active_text_files)):
                missing = [fn for fn in active_text_files if fn.lower() not in (full_response or "").lower()]
                correction = f"""
<RETRY_CORRECTION>
You failed to analyze all attached files.
You MUST include sections for these missing files:
{", ".join(missing)}
Re-run the response with the required per-file structure.
</RETRY_CORRECTION>
""".strip()

                retry_content = final_content + [correction]
                try:
                    full_response = run_model_once(google_chat, retry_content)
                except Exception:
                    try:
                        fallback_chat = client.chats.create(
                            model="gemini-1.5-flash",
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
                            history=history_for_google,
                        )
                        full_response = run_model_once(fallback_chat, retry_content)
                    except Exception as inner_e:
                        message_placeholder.error(f"David is overloaded. (Error: {inner_e})")
                        st.stop()

            # FIX: use correct parameter name user_text=
            full_response = validate_model_output(
                user_text=user_input,
                model_text=full_response,
                state=governance,
                expected_files_used=expected_used,
                task=task,
            )
            message_placeholder.markdown(full_response)

        # Optional legacy state advancement hooks
        if re.search(r"\bapprove\b.*\b(S1|narrative|usp|voice|claim boundaries)\b", user_input.lower()):
            governance["p1_s1_approved"] = True
            governance["claim_boundaries_approved"] = True

        if re.search(r"\bbrand kit complete\b|\bp1 exit\b", user_input.lower()):
            governance["p1_exit_complete"] = True

        active_chat["messages"].append({"role": "assistant", "content": full_response})
        active_chat["governance"] = governance
        save_ledger(st.session_state.all_chats)
