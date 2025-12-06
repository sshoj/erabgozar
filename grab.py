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
    
    /* Virtual Keyboard Button Styling */
    .stButton button {
        font-size: 1.5em !important;
        font-family: 'Tahoma', 'Arial', sans-serif !important;
        padding: 0.2rem 0.5rem !important;
        min-height: 50px;
        width: 100%;
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
if "lyrics_raw" not in st.session_state:
    st.session_state.lyrics_raw = ""
if "lyrics_processed" not in st.session_state:
    st.session_state.lyrics_processed = ""
# State for the editor buffer
if "editor_text" not in st.session_state:
    st.session_state.editor_text = ""
if "last_selected" not in st.session_state:
    st.session_state.last_selected = ""

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
    3. Select words to edit.
    4. Use the Virtual Keyboard to fix diacritics.
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

def append_to_editor(char):
    """Appends a character to the current editor text."""
    st.session_state.editor_text += char

def save_changes(original_selection, new_text):
    """Replaces the selected text in the main lyrics with the edited version."""
    if original_selection and st.session_state.lyrics_processed:
        # Simple string replacement - replaces all occurrences of the selection
        # For more precision, we would need index-based tracking, but this fits the current 'unique words' logic.
        st.session_state.lyrics_processed = st.session_state.lyrics_processed.replace(original_selection, new_text)
        st.success("Changes applied!")
        # Update the selection tracking so we don't overwrite the new text immediately
        st.session_state.last_selected = new_text 
        st.session_state.editor_text = new_text

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
                st.rerun()
        else:
            st.warning("Please enter some text first.")

    st.divider()

    # Processed Output & Interaction
    st.subheader("📖 Result (اعراب گذاری)")
    
    selected_word_string = ""
    
    if st.session_state.lyrics_processed:
        # 1. Show the full structured poem first (Readable View)
        st.markdown(f"""
        <div class='rtl-text'>{st.session_state.lyrics_processed}</div>
        """, unsafe_allow_html=True)
        
        # 2. Add Copy Button
        with st.expander("📋 Copy Text / کپی متن"):
            st.code(st.session_state.lyrics_processed, language="text")
        
        st.caption("👇 Select word(s) below to edit:")
        
        words = st.session_state.lyrics_processed.split()
        unique_words = list(dict.fromkeys(words))
        
        # 3. Selection Pills
        if hasattr(st, "pills"):
            selected_words_list = st.pills(
                "Word Selection",
                options=unique_words,
                selection_mode="multi",
                label_visibility="collapsed"
            )
        else:
            st.warning("Update Streamlit to use clickable pills. Using dropdown fallback.")
            selected_words_list = st.multiselect("Select words:", options=unique_words)

        if selected_words_list:
            selected_word_string = " ".join(selected_words_list)
            
    else:
        st.info("Generated lyrics will appear here.")

with col2:
    st.subheader("⌨️ Virtual Editor")
    
    if selected_word_string:
        # Check if selection changed to update the buffer
        if selected_word_string != st.session_state.last_selected:
            st.session_state.editor_text = selected_word_string
            st.session_state.last_selected = selected_word_string

        # Editor Input Area
        st.markdown("Edit the selected text below:")
        
        # Text Input for the word being edited
        # We use on_change to capture manual typing
        current_edit = st.text_input(
            "Editor",
            value=st.session_state.editor_text,
            key="editor_input",
            label_visibility="collapsed"
        )
        # Sync manual typing back to state
        if current_edit != st.session_state.editor_text:
             st.session_state.editor_text = current_edit

        st.markdown("---")
        st.caption("Add Diacritics:")

        # Virtual Keyboard Grid
        k_col1, k_col2, k_col3, k_col4 = st.columns(4)
        
        # Row 1: Short Vowels
        with k_col1:
            if st.button("َ", help="Fatha", key="btn_fatha"):
                append_to_editor("َ")
                st.rerun()
        with k_col2:
            if st.button("ِ", help="Kasra", key="btn_kasra"):
                append_to_editor("ِ")
                st.rerun()
        with k_col3:
            if st.button("ُ", help="Damma", key="btn_damma"):
                append_to_editor("ُ")
                st.rerun()
        with k_col4:
            if st.button("ّ", help="Tashdid", key="btn_tashdid"):
                append_to_editor("ّ")
                st.rerun()

        # Row 2: Others
        k_col5, k_col6, k_col7, k_col8 = st.columns(4)
        with k_col5:
            if st.button("ْ", help="Sokoun", key="btn_sokoun"):
                append_to_editor("ْ")
                st.rerun()
        with k_col6:
            if st.button("ً", help="Fathatan", key="btn_an"):
                append_to_editor("ً")
                st.rerun()
        with k_col7:
            if st.button("ٍ", help="Kasratan", key="btn_en"):
                append_to_editor("ٍ")
                st.rerun()
        with k_col8:
            if st.button("ٌ", help="Dammatan", key="btn_on"):
                append_to_editor("ٌ")
                st.rerun()
                
        st.markdown("---")
        
        # Save Button
        if st.button("💾 Apply Changes / ذخیره", type="primary", use_container_width=True):
            save_changes(selected_word_string, st.session_state.editor_text)
            st.rerun()
            
    else:
        st.info("👈 Select a word from the list to enable the virtual keyboard.")
        
        # Static display of keyboard for reference/preview (disabled look)
        st.caption("Virtual Keyboard Preview:")
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.button("َ", disabled=True, key="d1")
        p_col2.button("ِ", disabled=True, key="d2")
        p_col3.button("ُ", disabled=True, key="d3")
        p_col4.button("ّ", disabled=True, key="d4")

# --- Footer ---
st.markdown("---")
st.caption("Powered by Google Gemini API | Designed for Persian Poetry Analysis")
