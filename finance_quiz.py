import streamlit as st
import pandas as pd
import os
import json
from dotenv import load_dotenv

# Load configuration
load_dotenv()
PATHS = {
    "Caselet Quiz": os.getenv("CASELET_EXCEL_PATH", "Data/Caselets.xlsx"),
    "Numericals Quiz": os.getenv("NUMERICAL_EXCEL_PATH", "Data/Numericals.xlsx")
}

# --- Helper to load External Config ---
def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except Exception:
        return {
            "page_title": "Research Analysis Quiz",
            "instructions": ["Select a quiz to begin."],
            "disclaimer": "Educational purposes only."
        }

CONFIG = load_config()

st.set_page_config(page_title=CONFIG['page_title'], layout="wide")

def load_quiz_data(file_path, sheet_name, quiz_type):
    try:
        if quiz_type == "Caselet Quiz":
            df_raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            case_details = df_raw.iloc[0, 1]
            df_qs = df_raw.iloc[3:].copy()
            df_qs.columns = df_raw.iloc[2].tolist()
        else:
            df_qs = pd.read_excel(file_path, sheet_name=sheet_name)
            case_details = None
            
        df_qs = df_qs.dropna(subset=['Questiod_ID'], how='all')
        
        questions = []
        for _, row in df_qs.iterrows():
            q_data = {
                'case_details': case_details,
                'id': row.get('Questiod_ID'),
                'question': row.get('Question'),
                'options': {'A': row.get('Option A'), 'B': row.get('Option B'), 
                            'C': row.get('Option C'), 'D': row.get('Option D')},
                'answer': str(row.get('Answer')).strip().upper(),
                'explanation': row.get('Explanation')
            }
            if pd.notna(q_data['question']):
                questions.append(q_data)
        return questions
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return []

def go_home():
    # Hard reset of all keys including widget keys
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state.quiz_mode = "-- Select --"
    st.session_state.current_sheet = "-- Select --"
    st.session_state.confirmed = False

# --- Sidebar Navigation ---
st.sidebar.title("📚 Quiz Settings")

is_locked = st.session_state.get('confirmed', False) and not st.session_state.get('show_summary', False)

quiz_mode = st.sidebar.selectbox(
    "Select Quiz Type:", 
    ["-- Select --", "Caselet Quiz", "Numericals Quiz"],
    key="mode_selector",
    disabled=is_locked
)
st.session_state.quiz_mode = quiz_mode

if "last_mode" not in st.session_state or st.session_state.last_mode != quiz_mode:
    st.session_state.last_mode = quiz_mode
    st.session_state.current_sheet = "-- Select --"
    st.session_state.confirmed = False
    st.session_state.results = {}
    st.session_state.show_summary = False

if quiz_mode != "-- Select --":
    file_path = PATHS[quiz_mode]
    if os.path.exists(file_path):
        xl = pd.ExcelFile(file_path)
        sheet_options = ["-- Select --"] + xl.sheet_names
        selected_sheet = st.sidebar.selectbox(
            "Select Topic/Case:", 
            sheet_options, 
            key="sheet_selector",
            disabled=is_locked
        )
        
        if selected_sheet != st.session_state.get('current_sheet', "-- Select --"):
            st.session_state.current_sheet = selected_sheet
            st.session_state.confirmed = False
            st.session_state.q_idx = 0
            st.session_state.results = {}
            st.session_state.show_summary = False
            st.rerun()
    else:
        st.sidebar.error("Excel file not found.")
        selected_sheet = "-- Select --"
else:
    selected_sheet = "-- Select --"

# --- Main App Logic ---
if quiz_mode == "-- Select --" or selected_sheet == "-- Select --":
    st.title(CONFIG['page_title'])
    st.write("---")
    st.subheader("Welcome, Student!")
    
    # Instructions Section
    st.write("### Instructions")
    for item in CONFIG['instructions']:
        st.write(f"- {item}")
    
    # Disclaimer Section
    st.warning(f"**Disclaimer:** {CONFIG['disclaimer']}")

else:
    questions = load_quiz_data(PATHS[quiz_mode], selected_sheet, quiz_mode)
    
    # 1. Confirmation Stage
    if not st.session_state.get('confirmed', False):
        st.title(f"Confirm Start: {selected_sheet}")
        st.write(f"This quiz contains **{len(questions)} questions**.")
        if quiz_mode == "Caselet Quiz" and questions:
            with st.expander("🔍 Preview Case Study Details", expanded=True):
                details = questions[0]['case_details']
                if isinstance(details, str) and details.startswith("IMG:"):
                    img_path = os.path.join(os.path.dirname(PATHS[quiz_mode]), details.replace("IMG:", "").strip())
                    if os.path.exists(img_path): st.image(img_path, width='stretch')
                else: st.write(details)
        st.write("Are you ready to begin? The sidebar will be locked once you start.")
        col_start, col_cancel = st.columns([1, 5])
        with col_start:
            if st.button("✅ Start Quiz"):
                st.session_state.confirmed = True
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancel / Go Back"):
                go_home()
                st.rerun()

    # 2. Summary Stage
    elif st.session_state.get('show_summary', False):
        st.title(f"Performance Summary: {selected_sheet}")
        total = len(questions)
        correct = sum(1 for v in st.session_state.results.values() if v.get('is_correct'))
        accuracy = (correct / total * 100) if total > 0 else 0
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Questions", total)
        c2.metric("Correct ✅", correct)
        c3.metric("Unanswered 📝", total - len(st.session_state.results))
        c4.metric("Final Score %", f"{accuracy:.1f}%")
        st.divider()
        if st.button("🏠 Goto Home"):
            go_home()
            st.rerun()

    # 3. Checkpoint Stage
    elif st.session_state.get('show_checkpoint', False):
        st.title("⚠️ Unanswered Questions")
        unanswered_indices = [i for i in range(len(questions)) if i not in st.session_state.results]
        st.warning(f"You have **{len(unanswered_indices)}** unanswered questions remaining.")
        col_back, col_proceed = st.columns(2)
        with col_back:
            if st.button("⬅️ Review Unanswered"):
                st.session_state.q_idx = unanswered_indices[0]
                st.session_state.show_checkpoint = False
                st.rerun()
        with col_proceed:
            if st.button("Proceed to Summary 📊"):
                st.session_state.show_summary = True
                st.session_state.show_checkpoint = False
                st.rerun()

    # 4. Quiz Question Stage
    elif questions:
        current_q = questions[st.session_state.q_idx]
        st.title(f"{quiz_mode}: {selected_sheet}")
        if current_q['case_details']:
            with st.expander("📖 Case Study Details", expanded=True):
                details = current_q['case_details']
                if isinstance(details, str) and details.startswith("IMG:"):
                    img_path = os.path.join(os.path.dirname(PATHS[quiz_mode]), details.replace("IMG:", "").strip())
                    if os.path.exists(img_path): st.image(img_path, width='stretch')
                    else: st.error("Image missing.")
                else: st.write(details)

        st.subheader(f"Question {st.session_state.q_idx + 1} of {len(questions)}")
        st.write(f"**{current_q['question']}**")
        opts = current_q['options']
        labels = [f"Option {k}: {v}" for k, v in opts.items() if pd.notna(v)]
        already_answered = st.session_state.q_idx in st.session_state.results

        def on_answer_select():
            key = f"q_radio_{st.session_state.q_idx}"
            selected = st.session_state[key]
            if selected:
                user_letter = selected.split(":")[0].replace("Option ", "").strip()
                st.session_state.results[st.session_state.q_idx] = {
                    'is_correct': user_letter == current_q['answer'],
                    'choice_label': selected
                }

        st.radio(
            "Select your answer:", options=labels, 
            index=labels.index(st.session_state.results[st.session_state.q_idx]['choice_label']) if already_answered else None,
            key=f"q_radio_{st.session_state.q_idx}", on_change=on_answer_select, disabled=already_answered
        )

        if already_answered:
            res = st.session_state.results[st.session_state.q_idx]
            if res['is_correct']: st.success("✅ Correct answer")
            else: st.error(f"❌ Wrong answer. Correct: Option {current_q['answer']}")
            st.info(f"**Explanation:** {current_q['explanation']}")

        st.divider()
        n_prev, n_space, n_next = st.columns([1, 2, 1])
        with n_prev:
            if st.session_state.q_idx > 0:
                if st.button("⬅️ Previous"):
                    st.session_state.q_idx -= 1
                    st.rerun()
        with n_next:
            is_last = (st.session_state.q_idx == len(questions) - 1)
            btn_label = "End Quiz 🛑" if is_last else "Next ➡️"
            if st.button(btn_label):
                if is_last:
                    if len(st.session_state.results) < len(questions): st.session_state.show_checkpoint = True
                    else: st.session_state.show_summary = True
                else:
                    st.session_state.q_idx += 1
                st.rerun()
