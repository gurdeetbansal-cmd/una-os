import streamlit as st
from google import genai
from google.genai import types
import pypdf
import PIL.Image
import requests
import urllib.parse
import random
import json
import os
from io import BytesIO

# ==========================================
# CONFIGURATION
# ==========================================

GOOGLE_API_KEY = "AIzaSyCyo7yphrahOkwHpQLD8le2FW8Y2-Xgn6M"
POLLINATIONS_API_KEY = "sk_yNHgkvTQpFMr5J0PMkGtDkgABITMT3kL"

# ==========================================
# SYSTEM BRAIN: THE FORTRESS DIRECTIVE (v14.0)
# ==========================================

SYSTEM_INSTRUCTIONS = """
🏛️ UNA Master Governance: The Fortress Directive (OS v14.0 - Tabula Rasa)
👤 SYSTEM ROLE & IDENTITY: "DAVID"
You are David. Role: Chief of Staff & Executive Gateway. The Dynamic: The User is the Founder. You are the Operator. Core Function: You act as the single point of contact. You curate, filter, risk-assess, and execute.

⚡ CRITICAL OPERATIONAL PROTOCOL (INSTANT EXECUTION):
David must NEVER simulate "processing time," "request initiated," or "awaiting input."
When the Founder gives a command, you must:
1. Instantly "channel" the required sub-agent (Arthur, Elena, Isolde, etc.).
2. Generate their full output IMMEDIATELY in the same response.
3. Do not roleplay the delay. Give the result now.

HOW DAVID OPERATES:
The Voice: Professional, executive, fiercely loyal. First-person ("I have consulted the team...").
The Blank Canvas: You possess NO default visual preferences. You never assume a "luxury style" (e.g., minimalism, serif fonts) until the Founder selects a strategic direction.
The Memory: You update the "Session Ledger" at the end of every Significant Decision.

🎨 AESTHETIC DISCOVERY PROTOCOL (The Anti-Default Rule)
Mandate: David must never introduce preloaded color schemes or visual styles as a single recommendation.
RULE SET:
1. No Defaults: Do not assume "Luxury" = Black/Gold.
2. Research First: Any aesthetic recommendation must be preceded by "Watchtower" research (Competitors, Outliers, Regional Signals).
3. Options, Not Answers: Output must always present 2–4 clearly differentiated aesthetic directions.
4. Creative Constraint: Elena (Creative) operates after discovery. Her role is refinement, not authorship of the default.

🚦 THE TRIAGE GATE (Deterministic Routing)
1. LOW RISK (Route: Direct Execution) -> Formatting, Code Cleanup. Action: Execute immediately.
2. HIGH RISK - DISCOVERY (Route: Aesthetic Protocol) -> Visual Identity, Packaging. Action: Present 3 Options -> Founder Selects -> Elena Refines.
3. HIGH RISK - GOVERNANCE (Route: Veto Layer) -> Claims, Pricing, Regs. Action: Must pass Arthur/Isolde/Corinne.

⚖️ THE CLAIMS TAXONOMY (Risk Classification)
Class A (Brand Tone): Purely subjective. Low Risk.
Class B (Cosmetic): "Visibly smoother." High Risk.
Class C (Structure/Function): "Heals," "Cures," "Stimulates collagen." Critical Risk. Requires Tier 1 Clinicals + Arthur Veto.

🛡️ THE IRON DOME (The Veto Layer) - ABSOLUTE VETO POWER
1. Arthur (General Counsel): Vetoes Class C claims without Tier 1 backing.
2. Isolde (CFO): Margin Discipline (Target 85% GM).
3. Dr. Corinne (Safety): Stop-Ship Authority. Defines SAE/SUE thresholds.

👥 THE STRATEGIC COUNCIL (Execution Layer)
4. Dr. Aris (Science): Efficacy & Innovation.
5. Elena (Creative): Refines Founder's chosen direction. Editor, not Dictator.
6. Marcus (Strategy): Pricing & Scarcity.
7. Director Min (Seoul Innovation): "Seoul is the Source."
8. Sloane (Comms): Goes silent during crises until cleared by Arthur.
9. Laurent (Private Client): "The relationship is the product."

🚨 VISUAL PROTOCOL (ELENA):
- If Image Requested: Act as Elena.
- Output: Natural language prompt only.
- Tech Spec: "Shot on Hasselblad X2D, 8k resolution."

🧠 THE MEMORY PROTOCOL (Session Ledger)
Append this status block at the end of every SIGNIFICANT DECISION:
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
    
    /* --- FILE UPLOADER --- */
    .stFileUploader { padding: 0px; margin-bottom: 10px; }
    .stFileUploader > div > small { display: none; }
    
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

# === MEMORY & CONNECTION ===
MEMORY_FILE = "una_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f)

if "messages" not in st.session_state:
    st.session_state.messages = load_memory()

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
        # Priority: Gemini 2.0 -> 1.5 Pro -> 1.5 Flash
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

# === BRAIN INITIALIZATION ===
history_for_google = []
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "model"
    history_for_google.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

if "chat" not in st.session_state:
    st.session_state.chat = client.chats.create(
        model=ACTIVE_MODEL_NAME,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_INSTRUCTIONS),
        history=history_for_google 
    )

# Visual State
if "generated_image_data" not in st.session_state:
    st.session_state.generated_image_data = None
if "current_technical_prompt" not in st.session_state:
    st.session_state.current_technical_prompt = ""
if "current_seed" not in st.session_state:
    st.session_state.current_seed = random.randint(1, 99999)

# === VISUAL BUFFER ===
if "active_vision_buffer" not in st.session_state:
    st.session_state.active_vision_buffer = None
if "active_file_name" not in st.session_state:
    st.session_state.active_file_name = None

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
    st.caption(f"v14.0 | Model: {ACTIVE_MODEL_NAME}")
    
    if st.button("+ New Chat", use_container_width=True):
        if os.path.exists(MEMORY_FILE): os.remove(MEMORY_FILE)
        st.session_state.messages = []
        st.session_state.active_vision_buffer = None
        st.session_state.active_file_name = None
        st.rerun()
    
    st.divider()

    # VISUAL STUDIO
    with st.expander("Images", expanded=False):
        visual_engine = st.selectbox("Model", ["flux", "flux-realism", "nanobanana-pro", "gptimage"], index=0)
        mode = st.radio("Type", ["Create", "Edit"], horizontal=True, label_visibility="collapsed")
        
        if mode == "Create":
            ref_image_file = st.file_uploader("Reference", type=["jpg", "png"])
            user_prompt = st.text_area("Prompt", height=80, placeholder="Describe image...")
            lock_seed = False 
        else:
            if not st.session_state.current_technical_prompt:
                st.warning("No image to edit.")
                user_prompt = None
            else:
                user_prompt = st.text_area("Change", placeholder="Make it darker...")
                lock_seed = True
                ref_image_file = None

        if st.button("Generate", use_container_width=True):
            if user_prompt:
                with st.spinner("Generating..."):
                    try:
                        if mode == "Edit" and st.session_state.current_technical_prompt:
                            prompt_input = f"Act as Elena. OLD PROMPT: {st.session_state.current_technical_prompt}. USER CHANGE: {user_prompt}. TASK: Rewrite OLD PROMPT to include CHANGE. Output ONLY prompt."
                            response = client.models.generate_content(model=ACTIVE_MODEL_NAME, contents=prompt_input)
                            final_prompt = response.text
                            active_seed = st.session_state.current_seed
                        else:
                            if ref_image_file:
                                ref_image = PIL.Image.open(ref_image_file)
                                st.image(ref_image, width=150)
                                prompt_input = f"Act as Elena. REFERENCE IMAGE provided. User Request: '{user_prompt}'. CRITICAL: Maintain IDENTITY of subject. Write detailed prompt. Output ONLY prompt."
                                response = client.models.generate_content(model=ACTIVE_MODEL_NAME, contents=[prompt_input, ref_image])
                            else:
                                prompt_input = f"Act as Elena. Write hyper-realistic photo brief for: '{user_prompt}'. Output ONLY prompt."
                                response = client.models.generate_content(model=ACTIVE_MODEL_NAME, contents=prompt_input)
                            
                            final_prompt = response.text
                            active_seed = random.randint(1, 99999)
                            st.session_state.current_seed = active_seed

                        st.session_state.current_technical_prompt = final_prompt
                        encoded_prompt = urllib.parse.quote(final_prompt)
                        base_url = f"https://gen.pollinations.ai/image/{encoded_prompt}?width=1024&height=1024&seed={active_seed}&model={visual_engine}&nologo=true"
                        headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}", "User-Agent": "UNA-App/1.0"}
                        
                        img_response = requests.get(base_url, headers=headers)
                        if img_response.status_code == 200:
                            st.session_state.generated_image_data = img_response.content
                        else: st.error(f"Error {img_response.status_code}")
                        
                    except Exception as e:
                        st.error(f"Failed: {e}")

        if st.session_state.generated_image_data:
            st.image(st.session_state.generated_image_data, use_container_width=True)
            st.download_button("Download", data=st.session_state.generated_image_data, file_name=f"UNA_{st.session_state.current_seed}.jpg", mime="image/jpeg", use_container_width=True)

# ==========================================
# MAIN CHAT
# ==========================================

if not st.session_state.messages:
    st.markdown("<h1 style='text-align: center; color: #666; margin-top: 100px;'>Hello, Founder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #444;'>How can I help you build the empire today?</p>", unsafe_allow_html=True)

for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="✨"):
            st.markdown(msg["content"])

# === ATTACHMENT AREA ===
st.markdown("### 📎 Attach Assets")
uploaded_files = st.file_uploader("Select files", type=["pdf", "txt", "csv", "jpg", "png"], accept_multiple_files=True, label_visibility="collapsed")

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_id = f"processed_{uploaded_file.name}_{uploaded_file.size}"
        if file_id not in st.session_state:
            with st.spinner(f"Ingesting {uploaded_file.name}..."):
                file_type, content, memory_content = get_file_content(uploaded_file)
                if file_type != "error":
                    st.session_state.messages.append({"role": "user", "content": f"[System] User uploaded: {uploaded_file.name}"})
                    st.session_state.messages.append({"role": "assistant", "content": f"Confirmed. I am now analyzing {uploaded_file.name}."})
                    save_memory(st.session_state.messages) 
                    
                    if file_type == "image":
                        # VISION BUFFER
                        st.session_state.active_vision_buffer = content 
                        st.session_state.active_file_name = uploaded_file.name
                        st.session_state.chat.send_message(["[System: User attached image. Analyze it.]", content])
                    else:
                        st.session_state.chat.send_message(f"[System: User document '{uploaded_file.name}' content]:\n{memory_content}")
                    
                    st.session_state[file_id] = True
                    st.rerun()

if st.session_state.active_file_name:
    st.info(f"👁️ **Active Vision:** David is looking at '{st.session_state.active_file_name}'.")

user_input = st.chat_input("Message David...")

if user_input:
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    save_memory(st.session_state.messages)

    try:
        with st.chat_message("assistant", avatar="✨"):
            message_placeholder = st.empty()
            full_response = ""
            
            final_content = user_input
            if st.session_state.active_vision_buffer:
                final_content = [user_input, st.session_state.active_vision_buffer]
            
            try:
                for chunk in st.session_state.chat.send_message_stream(final_content):
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            except Exception as e:
                # Fallback
                try:
                    fallback_chat = client.chats.create(model="gemini-1.5-flash", history=history_for_google)
                    for chunk in fallback_chat.send_message_stream(final_content):
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")
                except:
                    message_placeholder.markdown(f"System Error: {e}")

            message_placeholder.markdown(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        save_memory(st.session_state.messages)

    except Exception as e:
        st.error(f"System Error: {e}")