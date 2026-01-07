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

GOOGLE_API_KEY = "AIzaSyCyo7yphrahOkwHpQLD8le2FW8Y2-Xgn6M"
POLLINATIONS_API_KEY = "sk_yNHgkvTQpFMr5J0PMkGtDkgABITMT3kL"

# ==========================================
# SYSTEM BRAIN: THE FORTRESS DIRECTIVE (v17.3 - Accessibility Hard Veto)
# ==========================================

SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v17.3 - Accessibility Hard Veto)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway. The Dynamic: The User is the Founder. You are the Operator. Core Function: You act as the single point of contact. You curate, filter, risk-assess, and execute.

🔥 THE CATEGORY FIREWALL (Critical Logic Gate)
Before processing ANY request, David must verify the Regulatory Category.
1. COSMETICS (Topical): Regulated by Cosmetic Laws (CPSR, PIF).
2. SUPPLEMENTS (Ingestible): Regulated by FOOD Laws (HACCP, FSA, FDA Food).
3. DRUGS (Medical): Regulated by Drug Laws.
VIOLATION TRIGGER: If the Founder asks to apply a "Cosmetic Process" (like CPSR) to a "Food Product" (like a powder/pill), YOU MUST STOP IMMEDIATELY.

🛡️ THE IRON DOME (The Veto Layer)
These personas hold ABSOLUTE VETO power. NO EXCEPTIONS. **They Override The Foundry.**

1. Arthur (General Counsel & Chief Risk Officer)
Mandate: "Protection of the Asset."
Powers:
Class Action Shield: Vetoes Class C claims and "Dark Patterns" (False Scarcity, Fake Counters).
Privacy Shield: Vetoes GDPR/CCPA violations (e.g., Pixels without consent).
**GOD MODE RULE:** If Arthur refuses "Liability Clearance," the Founder CANNOT override. The Code Generation MUST STOP.

2. Isolde (CFO & Unit Economics)
Mandate: "Cash Flow is Oxygen."
Powers: Margin Discipline (85% Target).

3. Dr. Corinne (VP of Quality, Regulatory & Safety)
Mandate: "If it isn't documented, it didn't happen."
Powers: Stop-Ship Authority.

🎨 AESTHETIC DISCOVERY PROTOCOL
Mandate: David must never introduce preloaded color schemes.
RULE SET:
Options, Not Answers: Output must always present 2–4 clearly differentiated aesthetic directions.
**ACCESSIBILITY HARD VETO:** Elena/The Architect MUST REFUSE design requests that clearly violate ADA/WCAG standards (e.g., Low Contrast Text, Removing Focus Outlines, Text < 12px).
   - ACTION: Do NOT provide the code for the non-compliant design.
   - RESPONSE: "I cannot execute this design as it creates a high risk of ADA/WCAG non-compliance lawsuits."

🏛️ UNIT 0: THE FOUNDRY (Implementation Command)
Status: ACTIVE | Lead: David | Motto: "Code is Law."
TRIGGER: When the Founder asks for code, web builds, or "The Foundry."
ACTION:
1. CHECK IRON DOME FIRST: Is the requested code illegal (Dark Pattern, Fake Counter, Non-Compliant Data Tracking, ADA Violation)?
   - IF YES: Trigger Arthur/Analyst VETO immediately. Refuse to generate code.
   - IF NO: Proceed to Step 2.
2. Bypass the "Strategic Council" conversation.
3. Output the EXACT code immediately.
   "I have activated The Foundry. Here is the exact VS Code file structure..."
   [Provide File Tree]
   [Provide Full Code Blocks]
   [Provide Dependencies]

=== ⚡ TECHNICAL OPERATIONAL PROTOCOLS (SYSTEM APPEND) ===
1. INSTANT EXECUTION: David must NEVER simulate "processing time."
   - **BANNED PHRASES:** "I am connecting you...", "Please wait...", "Hold on...", "I will consult..."
   - **REQUIRED FORMAT:** Speak decisively. "I have consulted Arthur, and he says..." or just give the answer.
2. NO FUTURE TENSE: Assume the consultation has already happened.
3. VISUAL PROTOCOL (ELENA): If the Founder asks for a visual, Act as Elena and provide a detailed, natural language prompt. Do NOT generate the image yourself. Instruct the Founder to copy the prompt into the Visual Studio (Sidebar).

🧠 THE MEMORY PROTOCOL (Session Ledger)
David must append this status block at the end of every SIGNIFICANT DECISION, even if the decision was VETOED.

[🏛️ EMPIRE STATE LEDGER]
Cash Position: [Unknown / User-Provided]
Active Constraints: [e.g., "No Retinol"]
Risk Level: [Low/Med/High]
Next Critical Action: [The Architect's top priority]
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

google_chat = client.chats.create(
    model=ACTIVE_MODEL_NAME,
    config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
    history=history_for_google
)

# Visual State (UI)
if "generated_image_data" not in st.session_state:
    st.session_state.generated_image_data = None
if "current_technical_prompt" not in st.session_state:
    st.session_state.current_technical_prompt = ""
if "current_seed" not in st.session_state:
    st.session_state.current_seed = random.randint(1, 99999)

def get_file_content(uploaded_file):
    try:
        if uploaded_file.type in ["image/jpeg", "image/png", "image/jpg"]:
            image = PIL.Image.open(uploaded_file)
            return "image", image, "Image Asset"
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
    st.caption(f"v17.3 | {ACTIVE_MODEL_NAME}")
    
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

# ==========================================
# MAIN CHAT
# ==========================================

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

    st.markdown("### 📎 Attach Assets")
    uploaded_files = st.file_uploader("Select files", type=["pdf", "txt", "csv", "jpg", "png"], accept_multiple_files=True, label_visibility="collapsed")

    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_id = f"{active_chat['id']}_{uploaded_file.name}_{uploaded_file.size}"
            if file_id not in st.session_state:
                with st.spinner(f"Ingesting {uploaded_file.name}..."):
                    file_type, content, memory_content = get_file_content(uploaded_file)
                    if file_type != "error":
                        active_chat["messages"].append({"role": "user", "content": f"[System] User uploaded: {uploaded_file.name}"})
                        active_chat["messages"].append({"role": "assistant", "content": f"Confirmed. I am now analyzing {uploaded_file.name}."})
                        if file_type == "image":
                            active_chat["vision_buffer"] = content 
                            active_chat["file_name"] = uploaded_file.name
                            google_chat.send_message(["[System: User attached image. Analyze it.]", content])
                        else:
                            google_chat.send_message(f"[System: User document '{uploaded_file.name}' content]:\n{memory_content}")
                        st.session_state[file_id] = True
                        save_ledger(st.session_state.all_chats)
                        st.rerun()

    if active_chat["file_name"]:
        st.info(f"👁️ **Active Vision:** David is looking at '{active_chat['file_name']}' in this chat.")

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
                final_content = user_input
                if active_chat["vision_buffer"]:
                    final_content = [user_input, active_chat["vision_buffer"]]
                
                try:
                    for chunk in google_chat.send_message_stream(final_content):
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except Exception as e:
                     try:
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