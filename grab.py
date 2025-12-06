import streamlit as st
import google.generativeai as genai
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Persian Lyrics Diacritics Studio",
    page_icon="✒️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS for RTL and Styling ---
st.markdown("""
<style>
    /* Force RTL for Persian text areas */
    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: 'Tahoma', 'Arial', sans-serif;
        font-size: 1.6em;
        line-height: 2.5em;
        white-space: pre-wrap; /* Preserve newlines */
        background-color: #fefae0 !important; /* Force parchment color */
        color: #000000 !important; /* Force black text for maximum contrast */
        padding: 25px;
        border-radius: 10px;
        border: 2px solid #d4a373 !important; /* Distinct border */
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* LTR Text for Finglish */
    .ltr-text {
        direction: ltr;
        text-align: left;
        font-family: 'Courier New', monospace;
        font-size: 1.4em;
        line-height: 2.0em;
        white-space: pre-wrap;
        background-color: #f0f4f8 !important; /* Light blue-grey */
        color: #000000 !important;
        padding: 25px;
        border-radius: 10px;
        border: 2px solid #6c757d !important;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    .stTextArea textarea {
        direction: rtl;
        font-family: 'Tahoma', 'Arial', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "lyrics_raw" not in st.session_state:
    st.session_state.lyrics_raw = ""
if "lyrics_processed" not in st.session_state:
    st.session_state.lyrics_processed = ""
if "lyrics_finglish" not in st.session_state:
    st.session_state.lyrics_finglish = ""

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Check secrets first, then env, then fallback to user input
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("API Key loaded from secrets! 🔒")
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            api_key = st.text_input("Gemini API Key", type="password", help="Get your key from aistudio.google.com")

    st.divider()
    
    st.info("""
    **How to use:**
    1. Enter Persian lyrics.
    2. Click 'Generate Outputs'.
    3. **Left:** Get Persian text with Diacritics.
    4. **Right:** Get Finglish text for Suno AI.
    """)
    
    model_choice = st.selectbox("Model", [
        "gemini-2.5-flash-preview-09-2025", 
        "gemini-1.5-pro", 
        "gemini-2.0-flash-exp", 
        "gemini-1.5-flash"
    ])

# --- Gemini API Setup ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_choice)
else:
    st.warning("Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

# --- Helper Functions ---
def generate_diacritics(text):
    """Calls Gemini to add diacritics to Persian text."""
    prompt = f"""
    لطفا این شعر فارسی را برای پرامپ موزیک اعراب گذاری کن.
    
    Strict Rules:
    1. Output ONLY the processed Persian text with diacritics.
    2. Do not add translations, explanations, or introductory text.
    3. Do NOT use the Sokoun diacritic ( ساکن / ْ ). Only use Fatha, Kasra, Damma, and Tashdid where necessary.
    
    Input Text:
    {text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating diacritics: {e}")
        return text

def generate_finglish(text):
    """Calls Gemini to create a Finglish version for Suno AI."""
    prompt = f"""
    Convert the following Persian lyrics into "Finglish" (Pinglish) specifically optimized for AI Music Generators like Suno AI.
    
    Strict Rules:
    1. The output must be phonetically accurate so an English-based AI reads it as Persian.
    2. Use clear spacing.
    3. Output ONLY the Finglish text. No explanations.
    4. Maintain the line structure of the original poem.
    
    Input Persian Text:
    {text}
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        st.error(f"Error generating finglish: {e}")
        return ""

# --- Main Layout ---
st.subheader("📝 Persian Lyrics Input")
raw_input = st.text_area("Paste your lyrics here:", value=st.session_state.lyrics_raw, height=120, label_visibility="collapsed")

if st.button("✨ Generate Outputs", type="primary", use_container_width=True):
    if raw_input:
        st.session_state.lyrics_raw = raw_input
        with st.spinner("Processing Lyrics (Diacritics & Finglish)..."):
            # Generate both concurrently (or sequentially for simplicity)
            st.session_state.lyrics_processed = generate_diacritics(raw_input)
            st.session_state.lyrics_finglish = generate_finglish(raw_input)
            st.rerun()
    else:
        st.warning("Please enter some text first.")

st.divider()

col1, col2 = st.columns(2, gap="large")

with col1:
    st.subheader("📖 Persian (اعراب گذاری)")
    if st.session_state.lyrics_processed:
        st.markdown(f"""
        <div class='rtl-text'>{st.session_state.lyrics_processed}</div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 Copy Persian / کپی متن"):
            st.code(st.session_state.lyrics_processed, language="text")
    else:
        st.info("Persian result with diacritics will appear here.")

with col2:
    st.subheader("🎵 Finglish (Suno AI)")
    if st.session_state.lyrics_finglish:
        st.markdown(f"""
        <div class='ltr-text'>{st.session_state.lyrics_finglish}</div>
        """, unsafe_allow_html=True)
        
        with st.expander("📋 Copy Finglish"):
            st.code(st.session_state.lyrics_finglish, language="text")
    else:
        st.info("Finglish transliteration will appear here.")

# --- Footer ---
st.markdown("---")
st.caption("Powered by Google Gemini API | Designed for Persian Poetry Analysis")
