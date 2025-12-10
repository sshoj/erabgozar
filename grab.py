import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import os
import time
import tempfile

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
    
    # --- Google Gemini Setup ---
    st.subheader("Google Gemini (Primary)")
    if "GOOGLE_API_KEY" in st.secrets:
        api_key = st.secrets["GOOGLE_API_KEY"]
        st.success("Gemini Key loaded! 🔒")
    else:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            api_key = st.text_input("Gemini API Key", type="password", help="Get your key from aistudio.google.com")

    model_choice = st.selectbox("Gemini Model", [
        "gemini-2.5-flash-preview-09-2025", 
        "gemini-1.5-pro", 
        "gemini-2.0-flash-exp", 
        "gemini-1.5-flash"
    ])

    st.divider()

    # --- OpenAI Fallback Setup ---
    st.subheader("OpenAI Fallback (Secondary)")
    st.caption("Auto-switches if Gemini quota exceeded.")
    
    if "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
        st.success("OpenAI Key loaded! 🔒")
    else:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            openai_api_key = st.text_input("OpenAI API Key", type="password", help="Required for fallback logic")
    
    # Updated to include GPT-5 Nano and Mini
    openai_model = st.selectbox("Fallback Model", ["gpt-5-nano", "gpt-5-mini", "gpt-4o-mini", "gpt-4o"])

    st.divider()
    
    st.info("""
    **How to use:**
    1. **Upload Music** to extract lyrics OR enter text manually.
    2. Click 'Generate Outputs'.
    3. **Left:** Get Persian text with Diacritics.
    4. **Right:** Get Finglish text for Suno AI.
    5. **Bottom:** Use Voice Input to correct the text.
    """)

# --- API Initialization ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_choice)
else:
    st.warning("Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

openai_client = None
if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)

# --- Helper Functions ---

class MockResponse:
    """Mock object to mimic Gemini response structure when using OpenAI."""
    def __init__(self, text):
        self.text = text

def generate_with_openai_fallback(contents):
    """Fallback function to generate text using OpenAI."""
    if not openai_client:
        return None
        
    try:
        prompt_parts = []
        
        # Check if contents is complex (list) or simple string
        if isinstance(contents, list):
            for item in contents:
                if isinstance(item, str):
                    prompt_parts.append(item)
                elif isinstance(item, dict) and "data" in item:
                    # Handle Audio for OpenAI Fallback using GPT-4o Transcribe
                    # We must save bytes to a temp file for the OpenAI library to read
                    try:
                        # Improved MIME type mapping to ensure correct file extension
                        suffix = ".wav" 
                        if "mime_type" in item:
                            mt = item["mime_type"].lower()
                            if "mpeg" in mt or "mp3" in mt: suffix = ".mp3"
                            elif "ogg" in mt: suffix = ".ogg"
                            elif "webm" in mt: suffix = ".webm"
                            elif "mp4" in mt or "m4a" in mt: suffix = ".m4a"
                            elif "flac" in mt: suffix = ".flac"
                            elif "wav" in mt: suffix = ".wav"

                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                            tmp_file.write(item["data"])
                            tmp_filepath = tmp_file.name
                        
                        # Transcribe audio using the superior gpt-4o-transcribe model
                        with open(tmp_filepath, "rb") as audio_file:
                            transcription = openai_client.audio.transcriptions.create(
                                model="gpt-4o-transcribe", 
                                file=audio_file,
                                language="fa" # Hint for Persian
                            )
                        
                        # Add transcription to prompt
                        prompt_parts.append(f"\n[Audio Transcription]: {transcription.text}\n")
                        
                        # Clean up temp file
                        os.unlink(tmp_filepath)
                        
                    except Exception as audio_err:
                        st.warning(f"Fallback Audio Processing Error: {audio_err}")
                        
        else:
            prompt_parts.append(contents)
            
        final_prompt = " ".join(prompt_parts)

        # Removed temperature=0.7 as reasoning models (like gpt-5-nano) often do not support it or require default (1)
        response = openai_client.chat.completions.create(
            model=openai_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant specialized in Persian poetry and lyrics. You must strictly follow formatting rules."},
                {"role": "user", "content": final_prompt}
            ]
        )
        return MockResponse(response.choices[0].message.content)
    except Exception as e:
        st.error(f"⚠️ OpenAI Fallback Failed: {e}")
        return None

def safe_generate_content(contents, **kwargs):
    """
    Wrapper for model.generate_content with exponential backoff and OpenAI fallback.
    """
    retries = 2
    delay = 1
    last_exception = None

    # 1. Try Gemini with Retries
    for attempt in range(retries):
        try:
            return model.generate_content(contents, **kwargs)
        except Exception as e:
            last_exception = e
            error_str = str(e).lower()
            # Catch wider range of resource/quota errors
            if any(k in error_str for k in ["429", "quota", "resource", "exhausted", "limit"]):
                time.sleep(delay)
                delay *= 2
            else:
                # Break loop for non-quota errors to fail fast or try fallback
                break
    
    # 2. If Gemini failed, try OpenAI Fallback
    error_str = str(last_exception).lower() if last_exception else ""
    # Broadened check for fallback trigger
    if any(k in error_str for k in ["quota", "429", "resource", "exhausted", "limit"]):
        if openai_client:
            st.warning(f"⚠️ Gemini Quota Exceeded. Switching to OpenAI ({openai_model}) for this request...")
            fallback_response = generate_with_openai_fallback(contents)
            if fallback_response:
                return fallback_response
        else:
            st.error("⚠️ **Quota Exceeded:** Rate limit hit. Add OpenAI API Key for fallback.")
            return None
    
    # 3. Final Error Reporting
    if last_exception:
        st.error(f"⚠️ **API Error:** {last_exception}")
    return None

def generate_diacritics(text):
    """Calls Gemini (or fallback) to add diacritics to Persian text."""
    prompt = f"""
    لطفا این شعر فارسی را برای پرامپ موزیک اعراب گذاری کن.
    
    Strict Rules:
    1. Output ONLY the processed Persian text with diacritics.
    2. **Persian-Specific Rules (CRITICAL):**
       - **NEVER** use Fatha (َ) before Aleph (ا).
       - **NEVER** use Sokoun (ْ) at all. It is not used in this style.
       - **ONLY** use Damma (ُ) before Vav (و) if the sound is specifically "oo" (like 'ooo'). Do not use it for 'ow'.
       - **NEVER** use Kasra (ِ) before Ye (ی) unless the sound is specifically "-ay".
    3. Use standard **Persian-style** diacritics (Harakat) for modern poetry.
       - Focus on Fatha (َ), Kasra (ِ), and Damma (ُ) for pronunciation clarity.
    4. Do not add translations, explanations, or introductory text.
    
    Input Text:
    {text}
    """
    response = safe_generate_content(prompt)
    if response:
        return response.text.strip()
    return text

def generate_finglish(text):
    """Calls Gemini (or fallback) to create a Finglish version for Suno AI."""
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
    response = safe_generate_content(prompt)
    if response:
        return response.text.strip()
    return ""

def extract_lyrics_from_audio(audio_bytes, mime_type):
    """Extracts Persian lyrics from an uploaded audio file using AI vocal focus."""
    prompt = """
    Listen to this audio file containing a Persian song.
    
    **AUDIO PROCESSING INSTRUCTION:** Focus strictly on the VOCAL track. Mentally separate the vocals from the background music, noise, and instrumentation. 
    Transcribe only the clear lyrical content.
    
    Task: Transcribe the lyrics exactly as sung in Persian.
    
    Rules:
    1. Output ONLY the Persian lyrics.
    2. Do not add translation or transliteration.
    3. Break lines according to the musical phrasing.
    4. Ignore instrumental parts and background noise.
    """
    response = safe_generate_content([
        prompt,
        {
            "mime_type": mime_type,
            "data": audio_bytes
        }
    ])
    if response:
        return response.text.strip()
    return ""

def process_voice_correction(current_text, audio_bytes):
    """Uses Gemini to correct text based on voice input."""
    prompt = f"""
    You are an expert Persian editor. 
    The user (a native speaker) has provided an audio recording to correct a SPECIFIC PART of the lyrics below.
    
    Task:
    1. Listen to the audio. The user is reciting a correction for a specific phrase or line.
    2. Locate that specific phrase in the "Current Persian Text".
    3. Replace ONLY that specific segment with the corrected version from the audio. 
    4. **DO NOT** regenerate or change the rest of the text. Keep surrounding text exactly as is.
    5. **CRITICAL Diacritic Rules:**
       - **NEVER** use Fatha (َ) before Aleph (ا).
       - **NEVER** use Sokoun (ْ).
       - **ONLY** use Damma (ُ) before Vav (و) if the sound is "oo".
       - **NEVER** use Kasra (ِ) before Ye (ی) unless it sounds like "-ay".
    6. Output the FULL text with the specific correction applied.
    
    Current Persian Text:
    {current_text}
    """
    response = safe_generate_content([
        prompt,
        {
            "mime_type": "audio/wav",
            "data": audio_bytes
        }
    ])
    if response:
        return response.text.strip()
    return current_text

# --- Main Layout ---
st.subheader("📝 Persian Lyrics Input")

# Audio Extraction Feature
with st.expander("🎵 Extract Lyrics from Audio File"):
    uploaded_file = st.file_uploader("Upload a Persian song (MP3, WAV, M4A, OGG)", type=['mp3', 'wav', 'm4a', 'ogg'])
    if uploaded_file is not None:
        if st.button("Extract Lyrics (AI Vocal Focus) & Auto-Generate"):
            with st.spinner("Listening, transcribing, and processing..."):
                audio_bytes = uploaded_file.read()
                extracted_text = extract_lyrics_from_audio(audio_bytes, uploaded_file.type)
                if extracted_text:
                    st.session_state.lyrics_raw = extracted_text
                    
                    # Automatically generate outputs
                    st.session_state.lyrics_processed = generate_diacritics(extracted_text)
                    st.session_state.lyrics_finglish = generate_finglish(extracted_text)
                    
                    st.success("Lyrics extracted and processed! Check results below.")
                    st.rerun()

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

# --- Voice Correction Section ---
st.markdown("---")
st.subheader("🎙️ Native Speaker Correction")
st.caption("Record your voice to correct a specific part of the lyrics. **Click once to start, and click again to stop.** The AI will only update the spoken part.")

audio_value = st.audio_input("Record correction")

if audio_value is not None:
    if st.button("Apply Voice Correction", type="primary"):
        if st.session_state.lyrics_processed:
            with st.spinner("Listening to correction and updating specific segment..."):
                # Get bytes from the UploadedFile object
                audio_bytes = audio_value.read()
                
                # 1. Update Persian Text (Partial Update Logic)
                corrected_persian = process_voice_correction(st.session_state.lyrics_processed, audio_bytes)
                st.session_state.lyrics_processed = corrected_persian
                
                # 2. Auto-update Finglish to match new Persian
                st.session_state.lyrics_finglish = generate_finglish(corrected_persian)
                
                st.success("Correction applied! Finglish has been updated as well.")
                st.rerun()
        else:
            st.warning("Generate text first before applying corrections.")

# --- Footer ---
st.markdown("---")
st.caption("Powered by Google Gemini API & OpenAI | Designed for Persian Poetry Analysis")
