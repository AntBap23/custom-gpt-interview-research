import streamlit as st
import json
import os
from dotenv import load_dotenv
from scripts.simulate_interviews import simulate_interview
from scripts.analyze_gioia import analyze_gioia
from scripts.export_results import export_both
from supabase_utils import sign_up, sign_in, get_user, get_user_plan, set_user_plan, insert_interview, upload_file, list_files
from stripe_utils import create_checkout_session

st.set_page_config(page_title="GPT Research SaaS", layout="wide")

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {
        'context': None,
        'table': None,
        'questions': None
    }
if 'personas' not in st.session_state:
    st.session_state.personas = []
if "user" not in st.session_state:
    st.session_state.user = None
if "plan" not in st.session_state:
    st.session_state.plan = "free"

# Load API key and validate
load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    st.warning("⚠️ OPENAI_API_KEY not found in .env file. Please add your API key to continue.")
    # Don't stop the app, just show warning

# Ensure required directories exist
for dir_path in ["personas", "data/ai_responses", "outputs", "questions"]:
    os.makedirs(dir_path, exist_ok=True)

st.title("🧠 GPT Research Interview Assistant")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Inputs", "👤 Add Personas", "💬 Simulate Interviews", "🔍 Analyze Themes"])

# --- Upload Inputs --- #
with tab1:
    st.header("Upload Research Materials")
    
    # Show current upload status
    if any(st.session_state.uploaded_files.values()):
        st.info("📁 Current Uploads:")
        for file_type, file in st.session_state.uploaded_files.items():
            if file:
                st.write(f"- {file_type.title()}: {file.name}")
    
    context_file = st.file_uploader("Upload Research Context (.docx)", type=["docx"])
    if context_file:
        st.session_state.uploaded_files['context'] = context_file
        st.success(f"✅ Context file uploaded: {context_file.name}")
    
    table_file = st.file_uploader("Upload Interviewee Table (.xlsx)", type=["xlsx"])
    if table_file:
        st.session_state.uploaded_files['table'] = table_file
        st.success(f"✅ Table file uploaded: {table_file.name}")
    
    question_file = st.file_uploader("Upload Interview Questions (.txt)", type=["txt"])
    if question_file:
        try:
            questions = [line.strip() for line in question_file.readlines() if line.strip()]
            if not questions:
                st.error("❌ No questions found in the uploaded file.")
            else:
                # Save questions to file
                questions_path = os.path.join("questions", "questions.txt")
                with open(questions_path, "w") as f:
                    f.write("\n".join(questions))
                st.session_state.questions = questions
                st.session_state.uploaded_files['questions'] = question_file
                st.success(f"✅ {len(questions)} questions loaded and saved.")
        except Exception as e:
            st.error(f"❌ Error processing questions file: {str(e)}")

# --- Add Personas --- #
with tab2:
    st.header("Create Persona")
    
    # Show existing personas
    existing_personas = [f for f in os.listdir("personas") if f.endswith('.json')]
    if existing_personas:
        st.info("👥 Existing Personas:")
        for persona in existing_personas:
            st.write(f"- {persona.replace('.json', '').replace('_', ' ').title()}")
    
    with st.form("persona_form"):
        name = st.text_input("Name")
        age = st.number_input("Age", 18, 99)
        job = st.text_input("Job")
        education = st.text_input("Education")
        personality = st.text_area("Personality Traits")
        ai_view = st.text_area("Opinion on AI")
        remote_view = st.text_area("Opinion on Remote Work")
        submitted = st.form_submit_button("Save Persona")

    if submitted:
        if not name or not job:
            st.error("❌ Name and Job are required fields.")
        else:
            try:
                data = {
                    "name": name,
                    "age": age,
                    "job": job,
                    "education": education,
                    "personality": personality,
                    "opinions": {
                        "AI": ai_view,
                        "Remote Work": remote_view
                    }
                }
                filename = f"personas/{name.lower().replace(' ', '_')}.json"
                with open(filename, "w") as f:
                    json.dump(data, f, indent=2)
                st.success(f"✅ Saved persona to {filename}")
                st.session_state.personas.append(name)
            except Exception as e:
                st.error(f"❌ Error saving persona: {str(e)}")

# --- Simulate Interviews --- #
with tab3:
    st.header("Simulate Interviews")
    
    # Show status of prerequisites
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.questions:
            st.success("✅ Questions loaded")
        else:
            st.warning("⚠️ Questions not loaded")
    
    with col2:
        persona_files = [f for f in os.listdir("personas") if f.endswith('.json')]
        if persona_files:
            st.success(f"✅ {len(persona_files)} personas found")
        else:
            st.warning("⚠️ No personas found")
    
    if not st.session_state.questions:
        st.warning("⚠️ Please upload questions in Tab 1 first.")
    elif not persona_files:
        st.warning("⚠️ Please create personas in Tab 2 first.")
    else:
        for persona_file in persona_files:
            persona_path = os.path.join("personas", persona_file)
            output_path = os.path.join("data", "ai_responses", persona_file.replace('.json', '_responses.json'))
            
            # Check if interview already exists
            interview_exists = os.path.exists(output_path)
            
            if interview_exists:
                st.info(f"📝 Interview already exists for {persona_file.replace('.json', '')}")
                if st.button(f"Re-run Interview for {persona_file}"):
                    try:
                        simulate_interview(persona_path, os.path.join("questions", "questions.txt"), output_path)
                        st.success(f"✅ Interview updated at {output_path}")
                    except Exception as e:
                        st.error(f"❌ Error simulating interview: {str(e)}")
            else:
                if st.button(f"Run Interview for {persona_file}"):
                    try:
                        simulate_interview(persona_path, os.path.join("questions", "questions.txt"), output_path)
                        st.success(f"✅ Interview saved to {output_path}")
                    except Exception as e:
                        st.error(f"❌ Error simulating interview: {str(e)}")

# --- Analyze Themes --- #
with tab4:
    st.header("Gioia Method Analysis")
    response_files = [f for f in os.listdir(os.path.join("data", "ai_responses")) if f.endswith('.json')]
    
    if not response_files:
        st.warning("⚠️ No interview responses found. Please simulate interviews in Tab 3 first.")
    else:
        selected_file = st.selectbox("Choose an interview to analyze:", response_files)
        
        # Show analysis status
        analysis_path = os.path.join("outputs", selected_file.replace('.json', '_gioia.md'))
        analysis_exists = os.path.exists(analysis_path)
        
        if analysis_exists:
            st.info("📊 Analysis already exists for this interview")
            if st.button("Re-run Gioia Analysis"):
                try:
                    analyze_gioia(os.path.join("data", "ai_responses", selected_file), analysis_path)
                    st.success(f"✅ Analysis updated at {analysis_path}")
                except Exception as e:
                    st.error(f"❌ Error running Gioia analysis: {str(e)}")
        else:
            if st.button("Run Gioia Analysis"):
                try:
                    analyze_gioia(os.path.join("data", "ai_responses", selected_file), analysis_path)
                    st.success(f"✅ Analysis saved to {analysis_path}")
                except Exception as e:
                    st.error(f"❌ Error running Gioia analysis: {str(e)}")

        # Export options
        st.subheader("Export Options")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export to DOCX"):
                try:
                    input_path = os.path.join("data", "ai_responses", selected_file)
                    base_name = selected_file.replace('.json', '')
                    export_both(input_path, base_name)
                    st.success("✅ Exported interview to DOCX")
                except Exception as e:
                    st.error(f"❌ Error exporting to DOCX: {str(e)}")
        
        with col2:
            if st.button("Export to PDF"):
                try:
                    input_path = os.path.join("data", "ai_responses", selected_file)
                    base_name = selected_file.replace('.json', '')
                    export_both(input_path, base_name)
                    st.success("✅ Exported interview to PDF")
                except Exception as e:
                    st.error(f"❌ Error exporting to PDF: {str(e)}")

def login_ui():
    st.header("Login / Sign Up")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        res = sign_in(email, password)
        if res.user:
            st.session_state.user = res.user
            st.session_state.plan = get_user_plan(res.user.id)
            st.success("Logged in!")
        else:
            st.error("Login failed.")
    if st.button("Sign Up"):
        res = sign_up(email, password)
        if res.user:
            st.success("Sign up successful! Please log in.")
        else:
            st.error("Sign up failed.")

def plan_ui():
    st.subheader(f"Your plan: {st.session_state.plan.title()}")
    if st.session_state.plan == "free":
        st.info("Upgrade to Pro for unlimited interviews and exports.")
        if st.button("Upgrade to Pro"):
            url = create_checkout_session(st.session_state.user.id, st.session_state.user.email)
            st.markdown(f"[Go to Stripe Checkout]({url})", unsafe_allow_html=True)
    else:
        st.success("You are a Pro user!")

def main_app():
    plan_ui()
    st.header("Upload Persona & Questions")
    persona = st.file_uploader("Persona JSON")
    questions = st.file_uploader("Questions TXT")
    if st.button("Upload Files") and persona and questions:
        upload_file(st.session_state.user.id, persona, persona.name)
        upload_file(st.session_state.user.id, questions, questions.name)
        st.success("Files uploaded!")
    st.header("Simulate Interview")
    if st.button("Run Interview"):
        if st.session_state.plan == "free":
            st.warning("Free users can only run 1 interview. Upgrade for more.")
        else:
            # Call your interview logic here
            st.success("Interview simulated! (placeholder)")
    st.header("Export Results")
    if st.session_state.plan == "pro":
        st.button("Export to DOCX/PDF")
    else:
        st.info("Upgrade to Pro to export results.")

if st.session_state.user is None:
    login_ui()
else:
    main_app()
