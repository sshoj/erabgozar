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
        font-size: 1.2em;
        line-height: 2em;
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
    }
    .ai-message {
        background-color: #e8f4f8;
        border-left: 5px solid #00a8e8;
    }
    /* Highlight selected word in display */
    .highlighted-word {
        background-color: #ffe4b5;
        padding: 2px 5px;
        border-radius: 4px;
        font-weight: bold;
        color: #d35400;
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
if "selected_word_index" not in st.session_state:
    st.session_state.selected_word_index = None

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    api_key = st.text_input("Gemini API Key", type="password", help="Get your key from aistudio.google.com")
    
    # Try to load from environment if not provided
    if not api_key:
        api_key = os.getenv("GOOGLE_API_KEY")

    st.divider()
    
    st.info("""
    **How to use:**
    1. Enter Persian lyrics.
    2. Click 'Add Diacritics'.
    3. Use the 'Word Inspector' to discuss specific words with Gemini.
    """)
    
    model_choice = st.selectbox("Model", ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-pro"])
    
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
    You are an expert in Persian literature and grammar. 
    Please add the correct diacritics (اعراب) to the following Persian lyrics to clarify pronunciation.
    Output ONLY the processed Persian text with diacritics. Do not add explanations.
    
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
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📝 Lyrics Editor")
    
    # Raw Input
    raw_input = st.text_area("Enter Persian Text (No Diacritics)", value=st.session_state.lyrics_raw, height=150, key="raw_input_area")
    
    if st.button("✨ Add Diacritics / Reset"):
        if raw_input:
            with st.spinner("Analyzing and adding اعراب..."):
                st.session_state.lyrics_raw = raw_input
                st.session_state.lyrics_processed = generate_diacritics(raw_input)
                # Reset chat on new generation
                st.session_state.messages = [] 
                st.rerun()
        else:
            st.warning("Please enter some text first.")

    st.divider()

    # Processed Output & Word Selection
    st.subheader("📖 Result with Diacritics")
    
    if st.session_state.lyrics_processed:
        # Split text into words for selection logic (simple split by space)
        # Note: This is a basic tokenizer. For complex Persian, a library like Hazm is better, but keeping it simple for one file.
        words = st.session_state.lyrics_processed.split()
        
        # Word Inspector
        st.write("👇 **Word Inspector:** Select a word to discuss or change.")
        
        # Create a list of options with index to handle duplicate words
        word_options = [f"{i}: {w}" for i, w in enumerate(words)]
        
        selected_option = st.selectbox(
            "Select word", 
            options=["None"] + word_options,
            label_visibility="collapsed"
        )
        
        selected_word = ""
        if selected_option != "None":
            idx = int(selected_option.split(":")[0])
            selected_word = words[idx]
            
            # Highlight Logic
            # Reconstruct text with HTML highlight
            highlighted_text = ""
            for i, w in enumerate(words):
                if i == idx:
                    highlighted_text += f"<span class='highlighted-word'>{w}</span> "
                else:
                    highlighted_text += f"{w} "
            
            st.markdown(f"<div class='rtl-text'>{highlighted_text}</div>", unsafe_allow_html=True)
        else:
            # Standard Display
            st.markdown(f"<div class='rtl-text'>{st.session_state.lyrics_processed}</div>", unsafe_allow_html=True)
            
    else:
        st.info("Generated lyrics will appear here.")

with col2:
    st.subheader("💬 Debate & Corrections")
    
    # Chat Container
    chat_container = st.container(height=400)
    
    with chat_container:
        if not st.session_state.messages:
            st.markdown("ask Gemini to critique the diacritics or suggest changes.")
            
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
    if selected_option != "None" and selected_word:
        st.caption(f"Selected: **{selected_word}**")
        col_act1, col_act2, col_act3 = st.columns(3)
        if col_act1.button("Why this form?"):
            default_prompt = f"Why did you use the form '{selected_word}'? Is there an alternative?"
        if col_act2.button("Change Word"):
            default_prompt = f"Please change '{selected_word}' to..."
        if col_act3.button("Is it poetic?"):
            default_prompt = f"Does '{selected_word}' fit the poetic meter here?"

    # The actual text input
    user_input = st.chat_input("Type your message here...", key="chat_input")
    
    # Handle Button Clicks (Buttons don't automatically submit chat_input, so we simulate submission)
    if default_prompt and not user_input:
        # If a button set the prompt, we treat it as the user input immediately
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
