import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
# Using the path from .env or defaulting to Data/Sample.xlsx
EXCEL_PATH = os.getenv("EXCEL_FILE_PATH", "Data/Sample.xlsx")
# Get the directory where the Excel file is located (Data/ folder)
DATA_DIR = os.path.dirname(EXCEL_PATH)

st.set_page_config(page_title="Finance Caselet Quiz", layout="wide")

def load_case_data(sheet_name):
    """Loads a specific sheet and parses it according to the B1/A3:H3 format."""
    try:
        # Load the specific sheet from Excel
        df_raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
        
        # B1: Case details or Image path (Row 0, Col 1)
        case_details = df_raw.iloc[0, 1]
        
        # A3:H3 is Header (Row 2), Data starts at Row 3 (index 3)
        df_questions = df_raw.iloc[3:].copy()
        df_questions.columns = df_raw.iloc[2].tolist()
        
        # Clean up empty rows based on Question ID
        df_questions = df_questions.dropna(subset=['Questiod_ID'], how='all')
        
        questions = []
        for _, row in df_questions.iterrows():
            q_data = {
                'case_details': case_details,
                'id': row.get('Questiod_ID'),
                'question': row.get('Question'),
                'options': {
                    'A': row.get('Option A'),
                    'B': row.get('Option B'),
                    'C': row.get('Option C'),
                    'D': row.get('Option D')
                },
                'answer': str(row.get('Answer')).strip().upper(),
                'explanation': row.get('Explanation')
            }
            # Only add valid questions
            if pd.notna(q_data['question']):
                questions.append(q_data)
        return questions
    except Exception as e:
        st.error(f"Error loading sheet '{sheet_name}': {e}")
        return []

# --- Initialize Session States ---
if 'results' not in st.session_state:
    st.session_state.results = {} # Tracks {question_index: is_correct}
if 'show_summary' not in st.session_state:
    st.session_state.show_summary = False
if 'q_idx' not in st.session_state:
    st.session_state.q_idx = 0

# --- Sidebar: Case Selection ---
st.sidebar.title("Quiz Navigation")

if os.path.exists(EXCEL_PATH):
    xl = pd.ExcelFile(EXCEL_PATH)
    sheet_names = xl.sheet_names
    selected_sheet = st.sidebar.selectbox("Select a Caselet:", sheet_names)
    
    # Reset local states if the user switches the Caselet sheet
    if "current_sheet" not in st.session_state or st.session_state.current_sheet != selected_sheet:
        st.session_state.current_sheet = selected_sheet
        st.session_state.q_idx = 0
        st.session_state.submitted = False
        st.session_state.results = {}
        st.session_state.show_summary = False
        st.rerun()

    questions = load_case_data(selected_sheet)

    if st.session_state.show_summary:
        # --- 📈 SUMMARY VIEW ---
        st.title(f"Quiz Summary: {selected_sheet}")
        total = len(questions)
        answered = len(st.session_state.results)
        correct = sum(1 for v in st.session_state.results.values() if v is True)
        wrong = answered - correct
        accuracy = (correct / answered * 100) if answered > 0 else 0

        # Display Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Questions", total)
        col2.metric("Correct ✅", correct)
        col3.metric("Wrong ❌", wrong)
        col4.metric("Accuracy %", f"{accuracy:.1f}%")

        if st.button("Restart Quiz"):
            st.session_state.show_summary = False
            st.session_state.q_idx = 0
            st.session_state.results = {}
            st.rerun()
    
    elif questions:
        # --- 📝 QUESTION VIEW ---
        current_q = questions[st.session_state.q_idx]
        st.title(f"Case: {selected_sheet}")

        # 1. Case Details (Image or Text)
        with st.expander("📖 View Case Details", expanded=True):
            content = current_q['case_details']
            
            # CHECK FOR IMAGE PREFIX
            if isinstance(content, str) and content.startswith("IMG:"):
                # Extract filename, e.g., "Case 5.png"
                img_filename = content.replace("IMG:", "").strip()
                img_path = os.path.join(DATA_DIR, img_filename)
                
                if os.path.exists(img_path):
                    # UPDATED: Replaced use_container_width with width='stretch'
                    st.image(img_path, caption=f"Case Study Image: {img_filename}", width='stretch')
                else:
                    st.error(f"Image file not found at: {img_path}")
            else:
                # Regular text caselet
                st.write(content)

        st.divider()

        # 2. Question Display
        st.subheader(f"Question {st.session_state.q_idx + 1}: {current_q['id']}")
        st.markdown(f"**{current_q['question']}**")

        # 3. Multiple Choice Options
        opts = current_q['options']
        labels = [f"Option {k}: {v}" for k, v in opts.items() if pd.notna(v)]
        
        choice = st.radio(
            "Choose one:",
            options=labels,
            index=None,
            key=f"radio_{selected_sheet}_{st.session_state.q_idx}"
        )

        if st.button("Submit Answer"):
            if choice:
                user_letter = choice.split(":")[0].replace("Option ", "").strip()
                is_correct = user_letter == current_q['answer']
                
                # Store result for summary
                st.session_state.results[st.session_state.q_idx] = is_correct
                
                # Immediate Feedback
                if is_correct:
                    st.markdown("### :green[Correct answer]")
                else:
                    st.markdown(f"### :red[Wrong answer]. Correct: Option {current_q['answer']}")
                
                # Show Explanation
                st.info(f"**Explanation:**\n\n{current_q['explanation']}")
            else:
                st.warning("Please select an answer first!")

        st.divider()

        # 4. Navigation (Previous / Next / Summary)
        col_prev, col_spacer, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.button("⬅️ Previous", disabled=(st.session_state.q_idx == 0)):
                st.session_state.q_idx -= 1
                st.rerun()

        with col_next:
            is_last = (st.session_state.q_idx == len(questions) - 1)
            next_label = "Summary 📊" if is_last else "Next ➡️"
            
            if st.button(next_label):
                if is_last:
                    st.session_state.show_summary = True
                else:
                    st.session_state.q_idx += 1
                st.rerun()

    else:
        st.warning("This sheet appears to be empty or formatted incorrectly.")

else:
    st.error(f"Excel file not found at {EXCEL_PATH}. Check your .env or Data folder.")
