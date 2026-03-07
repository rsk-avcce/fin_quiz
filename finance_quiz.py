import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Set page configuration
st.set_page_config(page_title="Finance Caselet Quiz", layout="wide")

# Path to your Excel file
EXCEL_PATH = os.path.join("Data", "Sample.xlsx")

def load_case_data(sheet_name):
    """Loads a specific sheet and parses it according to the B1/A3:H3 format."""
    try:
        # Load the specific sheet
        df_raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
        
        # B1: Case details (Row 0, Col 1)
        case_details = df_raw.iloc[0, 1]
        
        # A3:H3 is Header (Row 2), Data starts at Row 3
        df_questions = df_raw.iloc[3:].copy()
        df_questions.columns = df_raw.iloc[2].tolist()
        
        # Remove empty rows
        df_questions = df_questions.dropna(subset=['Questiod_ID', 'Question'], how='all')
        
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
            if pd.notna(q_data['question']):
                questions.append(q_data)
        return questions
    except Exception as e:
        st.error(f"Error loading sheet '{sheet_name}': {e}")
        return []

# --- Sidebar: Case Selection ---
st.sidebar.title("Quiz Navigation")

if os.path.exists(EXCEL_PATH):
    # Get all sheet names from the Excel file
    xl = pd.ExcelFile(EXCEL_PATH)
    sheet_names = xl.sheet_names
    
    selected_sheet = st.sidebar.selectbox("Select a Caselet:", sheet_names)
    
    # Reset question index if the sheet changes
    if "current_sheet" not in st.session_state or st.session_state.current_sheet != selected_sheet:
        st.session_state.current_sheet = selected_sheet
        st.session_state.q_idx = 0
        st.session_state.submitted = False
        st.session_state.selected_option = None

    # Load data for the selected sheet
    questions = load_case_data(selected_sheet)

    if questions:
        current_q = questions[st.session_state.q_idx]

        st.title(f"Finance Quiz: {selected_sheet}")

        # 1. Case Details (B1) - Repeated for all questions
        with st.expander("📖 View Case Details", expanded=True):
            st.write(current_q['case_details'])

        st.divider()

        # 2. Question Display
        st.subheader(f"Question {st.session_state.q_idx + 1}: {current_q['id']}")
        st.markdown(f"**{current_q['question']}**")

        # 3. Multiple Choice Options
        opts = current_q['options']
        labels = [f"Option {k}: {v}" for k, v in opts.items() if pd.notna(v)]
        
        # Use a form to handle submission cleanly
        choice = st.radio(
            "Choose one:",
            options=labels,
            index=None if not st.session_state.submitted else list(opts.keys()).index(st.session_state.selected_option),
            key=f"radio_{selected_sheet}_{st.session_state.q_idx}"
        )

        if not st.session_state.submitted:
            if st.button("Submit Answer"):
                if choice:
                    st.session_state.submitted = True
                    st.session_state.selected_option = choice.split(":")[0].replace("Option ", "").strip()
                    st.rerun()
                else:
                    st.warning("Please select an answer first!")

        # 4. Immediate Feedback & Explanation
        if st.session_state.submitted:
            correct_ans = current_q['answer']
            if st.session_state.selected_option == correct_ans:
                st.success("✅ Correct answer")
            else:
                st.error(f"❌ Wrong answer. Correct: {correct_ans}")
            
            st.info(f"**Explanation:**\n\n{current_q['explanation']}")

        st.divider()

        # 5. Navigation Buttons (Previous / Next)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=(st.session_state.q_idx == 0)):
                st.session_state.q_idx -= 1
                st.session_state.submitted = False
                st.session_state.selected_option = None
                st.rerun()

        with col3:
            if st.button("Next ➡️", disabled=(st.session_state.q_idx == len(questions) - 1)):
                st.session_state.q_idx += 1
                st.session_state.submitted = False
                st.session_state.selected_option = None
                st.rerun()

    else:
        st.warning("This sheet appears to be empty or formatted incorrectly.")

else:
    st.error(f"File not found at {EXCEL_PATH}. Please check the folder path.")