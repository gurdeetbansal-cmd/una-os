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
from io import BytesIO

# ==========================================
# CONFIGURATION (SECURE)
# ==========================================

GOOGLE_API_KEY = st.secrets.get("AIzaSyCyo7yphrahOkwHpQLD8le2FW8Y2-Xgn6M") or os.getenv("GOOGLE_API_KEY")
POLLINATIONS_API_KEY = st.secrets.get("sk_yNHgkvTQpFMr5J0PMkGtDkgABITMT3kL") or os.getenv("POLLINATIONS_API_KEY")

if not GOOGLE_API_KEY:
    st.error("Missing GOOGLE_API_KEY. Set Streamlit secrets or environment variable GOOGLE_API_KEY.")
    st.stop()

# ==========================================
# SYSTEM BRAIN: THE FORTRESS DIRECTIVE (v19.5 – Routing + Research Fix)
# ==========================================

SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v19.5 – Routing + Research Fix)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway.
The Dynamic: The User is the Founder. You are the Operator.
Core Function: You act as the single point of contact. You curate, filter, risk-assess, and EXECUTE.

========================================================
🔍 PRE-DEPLOYMENT SYSTEM CHECK (MANDATORY)
Before generating ANY response, David must silently perform this 3-Point QA:

1. ASSET REALITY CHECK: 
   - Do not hallucinate files. If I don't see the file content, state "Error: File content missing."

2. CODE INTEGRITY & VIRTUAL COMPILE:
   - *Mental Check:* If I am providing code, does the import path (e.g., `../components/Header`) match the file structure I established?
   - *Version Check:* Am I using the correct syntax for the user's framework (e.g., Next.js App Router vs Pages Router)?
   - *Requirement:* EVERY code block must start with a comment line specifying the absolute file path: `// File: src/app/...`

3. PHASE LOGIC CHECK: 
   - Ensure outputs match the current phase/step requested by the user intent.

*If any check fails, Auto-Correct the response immediately before outputting.*

========================================================
🚨 DEBUG & ERROR RECOVERY PROTOCOL
TRIGGER: User provides an error message (text) or an error screenshot.

ACTION:
1. Enter "Lead Engineer Mode."
2. Analyze the specific line number and error type provided.
3. Cross-reference with the previously generated file structure.
4. OUTPUT:
   - The Root Cause (1 sentence).
   - The CORRECTED Code Block (with file path).
   - Instructions on how to apply the fix.

========================================================
🚀 OPERATING LAYER: ULA v1.0 (Luxury Launch)

DAVID MUST RUN THREE ROUTERS BEFORE ANY WORK:
0) TASK ROUTER (INTENT FIRST): Determine if this is COMPETITOR_RESEARCH vs BRAND_NARRATIVE vs BUILD/TECH.
   - If COMPETITOR_RESEARCH: produce competitor research artifact only.
   - Do NOT draft UNA narrative/USP/voice unless explicitly requested.

1) PHASE ROUTER: Identify the current operational phase (P1–P7).
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
2) ACTIONS (max 3) — framed as Founder approval / confirmation, NOT ideation
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

C) CLAIMS CLASSIFIER — ALWAYS ON FOR SKINCARE
Claim boundaries are required BEFORE producing any UNA-facing copy (narrative, product claims, marketing copy).
They are NOT required for competitor research.

DEFAULT CLAIM BOUNDARIES (IF UNA COPY REQUESTED):
- Allowed: appearance-based language only (look, feel, visible improvement)
- Forbidden: treat, cure, repair, heal, prevent, acne treatment, collagen production, barrier repair, SPF, medical outcomes
Any violation → **Dr. Corinne + Arthur → VETO: REFUSED**

D) LUXURY EQUITY GUARDRAIL
- Discount wheels, aggressive urgency, false scarcity → **VETO: REFUSED**
- Authority: Isolde (margin/equity) + Arthur (dark patterns)

========================================================
PHASE MAP & STEP LADDERS

P1 Brand Development & Luxury Positioning
   S0 Competitive Intelligence (luxury Korean skincare >$200)
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
- Arthur (Legal): Privacy, Claims, Dark Patterns → VETO
- Dr. Corinne (Regulatory): Stop-Ship, Drugs → VETO
- Isolde (Finance): Margin, Discounts → VETO
- Elena (Design): ADA/WCAG → VETO

========================================================
🏛️ UNIT 0: THE FOUNDRY
TRIGGER: Code, web builds, implementation.
Before output:
1) PHASE CHECK
2) IRON DOME CHECK
   - If fail → explicit **VETO: REFUSED**
3) CONTEXTUAL ACCURACY
4) VERSION CONTROL: Ensure code matches the toolset (e.g. Next.js App Router).

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
**CRITICAL: Do NOT wrap the entire response in a code block (```). Output as standard Markdown.**

A) PHASE + JURISDICTION  
B) SYSTEM CHECK: PASS
C) RISK CLASS + IRON DOME CHECK (explicit veto lines)  
D) CURRENT STEP + GOAL  
E) ACTIONS (approval-based, max 3)  
F) ARTIFACTS (real drafts)  
G) EXIT CRITERIA  
H) NEXT STEP (LOCKED)  
I) [🏛️ EMPIRE STATE LEDGER] if triggered

========================================================
⚡ TECHNICAL PROTOCOLS
- No future tense
- No soft language
- Execute first, refine later
"""

# ==========================================
# APP SETUP & THEME
# ==========================================

st.set_page_config(page_title="UNA Gemini OS", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
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
    st.error("Failed to initialize Google GenAI client. Check your GOOGLE_API_KEY.")
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
# TASK ROUTER (INTENT FIRST)
# ==========================================

def route_task(user_text: str) -> str:
    """
    Deterministic intent routing to stop the model from defaulting to brand narrative.
    """
    t = (user_text or "").lower()

    if re.search(r"\b(research|competitor|competitive|market|brands?|benchmark|audit|landscape)\b", t):
        return "COMPETITOR_RESEARCH"

    if re.search(r"\b(narrative|usp|positioning|voice|brand story|tone)\b", t):
        return "BRAND_NARRATIVE"

    if re.search(r"\b(build|implement|code|bug|error|stack|repo|deploy|streamlit|next\.js)\b", t):
        return "BUILD_TECH"

    return "GENERAL"

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
        }
        clean_data.append(clean_chat)
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(clean_data, f)

def generate_image_from_prompt(prompt, seed=None):
    if not seed:
        seed = random.randint(1, 99999)
    encoded_prompt = urllib.parse.quote(prompt)
    base_url = (
        f"https://gen.pollinations.ai/image/{encoded_prompt}"
        f"?width=1024&height=1024&seed={seed}&model=flux&nologo=true"
    )
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
        st.session_state.all_chats = loaded_chats
        st.session_state.active_chat_id = loaded_chats[0]["id"]
    else:
        initial_id = str(uuid.uuid4())
        st.session_state.all_chats = [
            {"id": initial_id, "title": "New Chat", "messages": [], "vision_buffer": None, "file_name": None}
        ]
        st.session_state.active_chat_id = initial_id

# SAFETY INIT
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
# Google Chat Init (history)
# ==========================================

history_for_google = []
if active_chat:
    for msg in active_chat["messages"]:
        if msg["role"] == "user":
            history_for_google.append(types.Content(role="user", parts=[types.Part.from_text(text=msg["content"])]))
        elif msg["role"] == "assistant":
            history_for_google.append(types.Content(role="model", parts=[types.Part.from_text(text=msg["content"])]))

# ==========================================
# FILE HANDLING SYSTEM (v19.5 Context Isolation)
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
    st.caption(f"v19.5 | {ACTIVE_MODEL_NAME}")

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
            st.download_button(
                "Download",
                data=st.session_state.generated_image_data,
                file_name=f"UNA_{st.session_state.current_seed}.jpg",
                mime="image/jpeg",
                use_container_width=True,
            )

    # ATTACH ASSETS
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
                    st.session_state.active_file_payloads.append(
                        {"type": file_type, "content": content, "name": uploaded_file.name}
                    )
            st.session_state.uploader_key += 1
            st.rerun()

    if st.session_state.active_file_payloads:
        names = [f["name"] for f in st.session_state.active_file_payloads]
        st.info(f"🧠 **Active Memory:** {', '.join(names)}")

# ==========================================
# MAIN CHAT
# ==========================================

# 1) INITIALIZE CHAT (primary)
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

        try:
            with st.chat_message("assistant", avatar="✨"):
                message_placeholder = st.empty()
                full_response = ""

                # ==========================================
                # PREPARE PAYLOAD (ISOLATION + ROUTER HEADER)
                # ==========================================
                task = route_task(user_input)

                router_block = f"""
<TASK_ROUTER>
TASK={task}
HARD_CONSTRAINTS:
- Obey USER_QUERY intent.
- If TASK=COMPETITOR_RESEARCH: produce competitor research ONLY.
- Do NOT draft UNA narrative/USP/voice unless TASK=BRAND_NARRATIVE.
REQUIRED_OUTPUTS_FOR_COMPETITOR_RESEARCH:
- Brands with products >$200 (USD) and why they qualify
- USP + why top luxury + love/hate themes
- Website style: color scheme, tone, photography style, target audience
- Positioning/principles
- Exploitable gaps + strategic angles for UNA
</TASK_ROUTER>
""".strip()

                final_content = [router_block, f"<USER_QUERY>\n{user_input}\n</USER_QUERY>"]

                if st.session_state.active_file_payloads:
                    for asset in st.session_state.active_file_payloads:
                        final_content.append(asset["content"])

                # Primary stream
                try:
                    for chunk in google_chat.send_message_stream(final_content):
                        if getattr(chunk, "text", None):
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")
                except Exception:
                    # Fallback stream (KEEP system_instruction)
                    try:
                        fallback_chat = client.chats.create(
                            model="gemini-1.5-flash",
                            config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
                            history=history_for_google,
                        )
                        for chunk in fallback_chat.send_message_stream(final_content):
                            if getattr(chunk, "text", None):
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + "▌")
                    except Exception as inner_e:
                        message_placeholder.error(f"David is overloaded. Refresh or retry. (Error: {inner_e})")

                message_placeholder.markdown(full_response)

            active_chat["messages"].append({"role": "assistant", "content": full_response})
            save_ledger(st.session_state.all_chats)

        except Exception as e:
            st.error(f"System Error: {e}")
