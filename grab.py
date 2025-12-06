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
    .stTextArea textarea {
        direction: rtl;
        font-family: 'Tahoma', 'Arial', sans-serif;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background-color: #f0f2f6;
        border-left: 5px solid #4a4e69;
        color: #000000 !important;
    }
    .ai-message {
        background-color: #e8f4f8;
        border-left: 5px solid #00a8e8;
        color: #000000 !important;
    }
    
    /* Styling for Pills (Clickable words) to be RTL */
    div[data-testid="stPills"] {
        direction: rtl;
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: flex-start;
    }
    
    /* Adjust pill text */
    div[data-testid="stPills"] button {
        font-family: 'Tahoma', 'Arial', sans-serif !important;
        font-size: 1.0em !important;
        padding: 0.25rem 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "lyrics_raw" not in st.session_state:
    st.session_state.lyrics_raw = ""
if "lyrics_processed" not in st.session_state:
    st.session_state.lyrics_processed = ""

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
    2. Click 'Add Diacritics'.
    3. Read the generated poem.
    4. **Select a word** from the chips below to discuss or correct it.
    """)
    
    # Removed 3.0 as it is causing issues, defaulting to 2.5
    model_choice = st.selectbox("Model", [
        "gemini-2.5-flash-preview-09-2025", 
        "gemini-1.5-pro", 
        "gemini-2.0-flash-exp", 
        "gemini-1.5-flash"
    ])
    
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

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

def chat_with_gemini(user_query, context_lyrics):
    """Sends a message to Gemini with the current lyrics context."""
    history_prompt = "History of conversation:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-5:]])
    
    prompt = f"""
    You are a helpful and critical assistant helping a user edit Persian lyrics.
    
    Current Lyrics (with diacritics):
    {context_lyrics}
    
    {history_prompt}
    
    User Request: {user_query}
    
    If the user asks to change a specific word, provide the updated lyrics block in your response. 
    Explain your reasoning briefly if it involves grammar or poetic meter.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# --- Main Layout ---
col1, col2 = st.columns([1.2, 0.8], gap="large")

with col1:
    st.subheader("📝 Lyrics Editor")
    
    # Raw Input
    raw_input = st.text_area("Enter Persian Text (No Diacritics)", value=st.session_state.lyrics_raw, height=120, key="raw_input_area")
    
    if st.button("✨ Add Diacritics", type="primary"):
        if raw_input:
            with st.spinner("Analyzing and adding اعراب..."):
                st.session_state.lyrics_raw = raw_input
                st.session_state.lyrics_processed = generate_diacritics(raw_input)
                st.session_state.messages = [] 
                st.rerun()
        else:
            st.warning("Please enter some text first.")

    st.divider()

    # Processed Output & Interaction
    st.subheader("📖 Result (اعراب گذاری)")
    
    selected_word = ""
    
    if st.session_state.lyrics_processed:
        # 1. Show the full structured poem first (Readable View)
        # Using the updated css class for better visibility
        st.markdown(f"""
        <div class='rtl-text'>{st.session_state.lyrics_processed}</div>
        """, unsafe_allow_html=True)
        
        # 2. Add Copy Button functionality using st.code
        # This provides a native copy button for the user
        with st.expander("📋 Copy Text / کپی متن"):
            st.code(st.session_state.lyrics_processed, language="text")
        
        st.caption("👇 Select word(s) below to discuss or correct:")
        
        words = st.session_state.lyrics_processed.split()
        
        # Deduplicate words while preserving order for cleaner selection
        unique_words = list(dict.fromkeys(words))
        
        # 3. Show pills for selection (Interactive View)
        # Use st.pills for selection to avoid page reload issues
        if hasattr(st, "pills"):
            selected_words_list = st.pills(
                "Word Selection",
                options=unique_words,
                selection_mode="multi",
                label_visibility="collapsed"
            )
        else:
            # Fallback for older Streamlit versions
            st.warning("Update Streamlit to use clickable pills. Using dropdown fallback.")
            selected_words_list = st.multiselect("Select words:", options=unique_words)

        if selected_words_list:
            # Join selected words with space
            selected_word = " ".join(selected_words_list)
            
    else:
        st.info("Generated lyrics will appear here.")

with col2:
    st.subheader("💬 Debate & Corrections")
    
    # Chat Container
    chat_container = st.container(height=400)
    
    with chat_container:
        if not st.session_state.messages:
            if selected_word:
                st.markdown(f"**Selected:** `{selected_word}`\n\nAsk me about this!")
            else:
                st.markdown("Ask Gemini to critique the diacritics or suggest changes.")
            
        for msg in st.session_state.messages:
            if msg['role'] == 'user':
                st.markdown(f"""
                <div class='chat-message user-message'>
                    <strong>You</strong>
                    <div style='direction: rtl; text-align: right;'>{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='chat-message ai-message'>
                    <strong>Gemini</strong>
                    <div style='direction: rtl; text-align: right;'>{msg['content']}</div>
                </div>
                """, unsafe_allow_html=True)

    # Chat Input Area
    st.divider()
    
    # Contextual Input Construction
    default_prompt = ""
    
    if selected_word:
        st.caption(f"Talking about: **{selected_word}**")
        col_act1, col_act2 = st.columns(2)
        if col_act1.button("Why this form?", use_container_width=True):
            default_prompt = f"Regarding the word(s) '{selected_word}': Why did you choose this specific form/diacritic? Is there an alternative?"
        if col_act2.button("Fix & Regenerate", use_container_width=True):
            default_prompt = f"The word '{selected_word}' is incorrect. Please fix the diacritics for this word and regenerate the full lyrics."

    # The actual text input
    user_input = st.chat_input("Type your message here...", key="chat_input")
    
    # Handle Button Clicks
    if default_prompt and not user_input:
        user_input = default_prompt

    if user_input:
        # Add User Message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Add AI Response
        with st.spinner("Thinking..."):
            ai_reply = chat_with_gemini(user_input, st.session_state.lyrics_processed)
            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        
        st.rerun()

# --- Footer ---
st.markdown("---")
st.caption("Powered by Google Gemini API | Designed for Persian Poetry Analysis")
