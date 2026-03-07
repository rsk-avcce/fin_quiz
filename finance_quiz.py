import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
EXCEL_PATH = os.getenv("EXCEL_FILE_PATH", "Data/Sample.xlsx")

st.set_page_config(page_title="Finance Quiz", layout="wide")

def load_case_data(sheet_name):
    try:
        df_raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name, header=None)
        case_details = df_raw.iloc[0, 1]
        df_questions = df_raw.iloc[3:].copy()
        df_questions.columns = df_raw.iloc[2].tolist()
        df_questions = df_questions.dropna(subset=['Questiod_ID'], how='all')
        
        questions = []
        for _, row in df_questions.iterrows():
            q_data = {
                'case_details': case_details,
                'id': row.get('Questiod_ID'),
                'question': row.get('Question'),
                'options': {'A': row.get('Option A'), 'B': row.get('Option B'), 
                            'C': row.get('Option C'), 'D': row.get('Option D')},
                'answer': str(row.get('Answer')).strip().upper(),
                'explanation': row.get('Explanation')
            }
            questions.append(q_data)
        return questions
    except Exception as e:
        st.error(f"Error: {e}")
        return []

# Initialize Session States
if 'results' not in st.session_state:
    st.session_state.results = {} # Stores {q_idx: is_correct}
if 'show_summary' not in st.session_state:
    st.session_state.show_summary = False

st.sidebar.title("Quiz Navigation")
if os.path.exists(EXCEL_PATH):
    xl = pd.ExcelFile(EXCEL_PATH)
    sheet_names = xl.sheet_names
    selected_sheet = st.sidebar.selectbox("Select Caselet:", sheet_names)

    # Reset state if sheet changes
    if "current_sheet" not in st.session_state or st.session_state.current_sheet != selected_sheet:
        st.session_state.current_sheet = selected_sheet
        st.session_state.q_idx = 0
        st.session_state.submitted = False
        st.session_state.results = {}
        st.session_state.show_summary = False
        st.rerun()

    questions = load_case_data(selected_sheet)

    if st.session_state.show_summary:
        # --- SUMMARY VIEW ---
        st.title(f"Quiz Summary: {selected_sheet}")
        total = len(questions)
        answered = len(st.session_state.results)
        correct = sum(1 for v in st.session_state.results.values() if v is True)
        wrong = answered - correct
        accuracy = (correct / answered * 100) if answered > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Questions", total)
        col2.metric("Correct", correct)
        col3.metric("Wrong", wrong)
        col4.metric("Accuracy", f"{accuracy:.1f}%")

        

        if st.button("Restart Quiz"):
            st.session_state.show_summary = False
            st.session_state.q_idx = 0
            st.session_state.results = {}
            st.rerun()
    
    elif questions:
        # --- QUESTION VIEW ---
        current_q = questions[st.session_state.q_idx]
        st.title(f"{selected_sheet}")
        with st.expander("📖 Case Details", expanded=True):
            st.write(current_q['case_details'])

        st.subheader(f"Question {st.session_state.q_idx + 1}: {current_q['question']}")
        
        opts = current_q['options']
        labels = [f"Option {k}: {v}" for k, v in opts.items() if pd.notna(v)]
        
        choice = st.radio("Select Answer:", options=labels, index=None, key=f"r_{st.session_state.q_idx}")

        if st.button("Submit Answer"):
            if choice:
                user_letter = choice.split(":")[0].replace("Option ", "").strip()
                is_correct = user_letter == current_q['answer']
                st.session_state.results[st.session_state.q_idx] = is_correct
                
                if is_correct:
                    st.success("Correct answer")
                else:
                    st.error(f"Wrong answer. Correct is {current_q['answer']}")
                st.info(f"**Explanation:** {current_q['explanation']}")
            else:
                st.warning("Please select an option.")

        # Navigation
        st.divider()
        nav_prev, nav_mid, nav_next = st.columns([1, 2, 1])
        
        with nav_prev:
            if st.button("Previous", disabled=(st.session_state.q_idx == 0)):
                st.session_state.q_idx -= 1
                st.rerun()

        with nav_next:
            is_last = st.session_state.q_idx == len(questions) - 1
            btn_label = "Summary" if is_last else "Next"
            
            if st.button(btn_label):
                if is_last:
                    st.session_state.show_summary = True
                else:
                    st.session_state.q_idx += 1
                st.rerun()
