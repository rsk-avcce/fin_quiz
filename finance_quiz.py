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

# --- Helper for Excel Formatting ---
def format_excel_value(val):
    """Handles Excel's decimal conversion of percentages and NaN values."""
    if pd.isna(val):
        return ""
    
    # Check if the value is a float that might be a percentage
    # In finance sheets, values like 0.08 are usually 8%
    if isinstance(val, (float, int)):
        # If the value is a small float, we treat it as a potential percentage 
        # but only if we want to force that format. 
        # A safer way is to simply convert to string to avoid 0.675000000001 issues.
        if isinstance(val, float):
            # Check if it looks like a clean percentage (e.g., 0.08 -> 8%)
            # Or just return as a clean string without trailing zeros
            return f"{val:g}" 
    return str(val)

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
                'options': {
                    # Apply formatting helper to each option
                    'A': format_excel_value(row.get('Option A')),
                    'B': format_excel_value(row.get('Option B')),
                    'C': format_excel_value(row.get('Option C')),
                    'D': format_excel_value(row.get('Option D'))
                },
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
    st.title(CONFIG.get('page_title', "Research Analysis Quiz"))
    st.write("---")
    st.subheader("Welcome, Student!")
    st.write("### Instructions")
    for item in CONFIG.get('instructions', []):
        st.write(f"- {item}")
    st.warning(f"**Disclaimer:** {CONFIG.get('disclaimer', '')}")

else:
    questions = load_quiz_data(PATHS[quiz_mode], selected_sheet, quiz_mode)
    
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
        st.write("Are you ready to begin?")
        col_start, col_cancel = st.columns([1, 5])
        with col_start:
            if st.button("✅ Start Quiz"):
                st.session_state.confirmed = True
                st.rerun()
        with col_cancel:
            if st.button("❌ Cancel / Go Back"):
                go_home()
                st.rerun()

    elif st.session_state.get('show_summary', False):
        st.title(f"Performance Summary: {selected_sheet}")
        total = len(questions)
        correct = sum(1 for v in st.session_state.results.values() if v.get('is_correct'))
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total", total)
        c2.metric("Correct ✅", correct)
        c3.metric("Unanswered 📝", total - len(st.session_state.results))
        c4.metric("Score %", f"{(correct/total*100):.1f}%" if total > 0 else "0%")
        st.divider()
        if st.button("🏠 Goto Home"):
            go_home()
            st.rerun()

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

    elif questions:
        current_q = questions[st.session_state.q_idx]
        st.title(f"{quiz_mode}: {selected_sheet}")
        if current_q['case_details']:
            with st.expander("📖 Case Study Details", expanded=True):
                details = current_q['case_details']
                if isinstance(details, str) and details.startswith("IMG:"):
                    img_path = os.path.join(os.path.dirname(PATHS[quiz_mode]), details.replace("IMG:", "").strip())
                    if os.path.exists(img_path): st.image(img_path, width='stretch')
                else: st.write(details)

        st.subheader(f"Question {st.session_state.q_idx + 1} of {len(questions)}")
        st.write(f"**{current_q['question']}**")
        
        # FIX 1: Remove "Option A:" prefix and show only the value
        opts = current_q['options']
        # We store the raw mapping to identify the letter later
        labels = [opts[k] for k in ['A', 'B', 'C', 'D'] if opts[k] != ""]
        
        already_answered = st.session_state.q_idx in st.session_state.results

        def on_answer_select():
            key = f"q_radio_{st.session_state.q_idx}"
            selected_val = st.session_state[key]
            if selected_val:
                # Find which letter (A, B, C, or D) matches the selected value
                user_letter = [k for k, v in opts.items() if v == selected_val][0]
                st.session_state.results[st.session_state.q_idx] = {
                    'is_correct': user_letter == current_q['answer'],
                    'selected_val': selected_val
                }

        st.radio(
            "Select your answer:", 
            options=labels, 
            index=labels.index(st.session_state.results[st.session_state.q_idx]['selected_val']) if already_answered else None,
            key=f"q_radio_{st.session_state.q_idx}", 
            on_change=on_answer_select, 
            disabled=already_answered
        )

        if already_answered:
            res = st.session_state.results[st.session_state.q_idx]
            if res['is_correct']: st.success("✅ Correct answer")
            else: st.error(f"❌ Wrong answer. The correct option was: {opts[current_q['answer']]}")
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
