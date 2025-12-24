import streamlit as st
import json
import os
import openai
from config import get_secret
from scripts.simulate_interviews import simulate_interview
from scripts.analyze_gioia import analyze_gioia
from scripts.export_results import export_both
from utils.pdf_parser import extract_text_from_pdf, extract_questions_with_ai, validate_and_improve_questions
from utils.persona_parser import extract_text_from_docx, extract_text_from_pdf_persona, extract_persona_info_with_ai, validate_persona_data

st.set_page_config(page_title="GPT Research SaaS", layout="wide")

# Initialize session state
if 'questions' not in st.session_state:
    st.session_state.questions = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = {
        'context': None,
        'questions': None
    }
if 'personas' not in st.session_state:
    st.session_state.personas = []

# Load API key from secrets (no .env dependency)
api_key = get_secret("OPENAI_API_KEY")
if not api_key:
    st.sidebar.error("No OpenAI API key configured")
    st.sidebar.warning(
        "Set OPENAI_API_KEY in Streamlit secrets (secrets.toml or Cloud Secrets)."
    )

# Ensure required directories exist
for dir_path in ["personas", "data/ai_responses", "outputs", "questions"]:
    os.makedirs(dir_path, exist_ok=True)

# Preload questions from disk if available (ensures Simulate tab sees them)
questions_file_path = os.path.join("questions", "questions.txt")
if os.path.exists(questions_file_path) and not st.session_state.questions:
    try:
        with open(questions_file_path, "r") as f:
            st.session_state.questions = [line.strip() for line in f if line.strip()]
    except Exception:
        pass

st.title("AI vs Real Interview Comparison Tool")

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Upload Real Interview", "Add Personas", "Simulate AI Interviews", "Compare & Analyze"])

# --- Upload Inputs --- #
with tab1:
    st.header("Upload Real Interview Data")
    st.info("**Purpose:** Upload your actual interview transcript to compare against AI-generated responses using the same questions and personas.")
    
    # Show current upload status
    if any(st.session_state.uploaded_files.values()):
        st.info("Current Uploads:")
        for file_type, file in st.session_state.uploaded_files.items():
            if file:
                st.write(f"- {file_type.title()}: {file.name}")
    
    # Real interview transcript upload
    st.subheader("Upload Real Interview Transcript")
    context_file = st.file_uploader("Upload Real Interview Transcript", type=["docx", "pdf", "txt"])
    if context_file:
        try:
            # Extract text based on file type
            if context_file.type == "application/pdf":
                st.info("Extracting text from PDF transcript...")
                transcript_text = extract_text_from_pdf(context_file)
            elif context_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                st.info("Extracting text from DOCX transcript...")
                transcript_text = extract_text_from_docx(context_file)
            else:  # txt file
                transcript_text = str(context_file.read(), "utf-8")
            
            if transcript_text:
                st.success(f"Extracted {len(transcript_text)} characters from transcript")
                
                # Show transcript preview
                with st.expander("View Transcript Preview"):
                    st.text_area("Transcript Text", transcript_text[:1000] + "..." if len(transcript_text) > 1000 else transcript_text, height=200)
                
                # Save transcript (internal) and provide download
                transcript_path = os.path.join("data", "real_interview_transcript.txt")
                os.makedirs("data", exist_ok=True)
                with open(transcript_path, "w") as f:
                    f.write(transcript_text)
                st.session_state.uploaded_files['context'] = context_file
                st.success("Real interview transcript ready")
                st.download_button(
                    label="Download Transcript",
                    data=transcript_text,
                    file_name=os.path.basename(context_file.name if hasattr(context_file, 'name') else 'real_interview_transcript.txt'),
                    mime="text/plain",
                    key="download_transcript_tab1"
                )
            else:
                st.error("Could not extract text from transcript file")
                
        except Exception as e:
            st.error(f"Error processing transcript: {str(e)}")
    
    # Enhanced question file upload with PDF support
    st.subheader("Upload Interview Questions")
    question_file = st.file_uploader("Upload Interview Questions", type=["txt", "pdf"])
    
    if question_file:
        try:
            questions = []
            
            if question_file.type == "application/pdf":
                st.info("Extracting text from PDF...")
                
                # Extract text from PDF
                pdf_text = extract_text_from_pdf(question_file)
                
                if pdf_text:
                    st.success(f"Extracted {len(pdf_text)} characters from PDF")
                    
                    # Show extracted text preview
                    with st.expander("View Extracted Text Preview"):
                        st.text_area("Extracted Text", pdf_text[:1000] + "..." if len(pdf_text) > 1000 else pdf_text, height=200)
                    
                    # Use AI to extract questions
                    st.info("Using AI to identify interview questions...")
                    questions = extract_questions_with_ai(pdf_text)
                    
                    if questions:
                        st.success(f"AI identified {len(questions)} potential questions")
                        
                        # Option to improve questions with AI
                        if st.button("Improve Questions with AI"):
                            with st.spinner("Improving questions..."):
                                improved_questions = validate_and_improve_questions(questions)
                                if improved_questions:
                                    questions = improved_questions
                                    st.success("Questions improved!")
                    else:
                        st.warning("No questions found by AI. Please check the PDF content.")
                        
                else:
                    st.error("Could not extract text from PDF. Please try a different file.")
                    
            else:  # Text file
                questions = [line.strip() for line in question_file.readlines() if line.strip()]
            
            if questions:
                # Auto-save immediately and sync session state
                try:
                    questions_path = os.path.join("questions", "questions.txt")
                    with open(questions_path, "w") as f:
                        f.write("\n".join(questions))
                    st.session_state.questions = questions
                    st.session_state.uploaded_files['questions'] = question_file
                    st.info(f"{len(questions)} questions loaded")
                except Exception as e:
                    st.warning(f"Could not auto-save questions: {str(e)}")

                # Display extracted/loaded questions
                st.subheader("Extracted Questions:")
                for i, question in enumerate(questions, 1):
                    st.write(f"{i}. {question}")
                
                # Allow manual editing
                with st.expander("Edit Questions Manually"):
                    edited_questions = st.text_area(
                        "Edit questions (one per line):",
                        "\n".join(questions),
                        height=300
                    )
                    if st.button("Update Questions"):
                        questions = [line.strip() for line in edited_questions.split('\n') if line.strip()]
                        st.success(f"Updated to {len(questions)} questions")
                
                # Save questions
                if st.button("Save Edited Questions"):
                    questions_path = os.path.join("questions", "questions.txt")
                    with open(questions_path, "w") as f:
                        f.write("\n".join(questions))
                    st.session_state.questions = questions
                    st.session_state.uploaded_files['questions'] = question_file
                    st.success(f"{len(questions)} questions saved successfully!")
                    
            elif question_file.type != "application/pdf":
                st.error("No questions found in the uploaded file.")
                
        except Exception as e:
            st.error(f"Error processing questions file: {str(e)}")

# --- Add Personas --- #
with tab2:
    st.header("Create Persona")
    
    # Show existing personas
    existing_personas = [f for f in os.listdir("personas") if f.endswith('.json')]
    if existing_personas:
        st.info("Existing Personas:")
        for persona in existing_personas:
            st.write(f"- {persona.replace('.json', '').replace('_', ' ').title()}")
    
    # Persona creation method selection
    creation_method = st.radio(
        "Choose persona creation method:",
        ["Manual Entry", "Upload Document (PDF/DOCX)"],
        horizontal=True
    )
    
    if creation_method == "Upload Document (PDF/DOCX)":
        st.subheader("Upload Persona Document")
        persona_file = st.file_uploader("Upload persona document", type=["pdf", "docx"])
        
        if persona_file:
            try:
                # Get persona counter for naming
                persona_counter = len(existing_personas) + 1
                
                # Extract text based on file type
                if persona_file.type == "application/pdf":
                    st.info("Extracting text from PDF...")
                    document_text = extract_text_from_pdf_persona(persona_file)
                elif persona_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    st.info("Extracting text from DOCX...")
                    document_text = extract_text_from_docx(persona_file)
                else:
                    st.error("Unsupported file type")
                    document_text = ""
                
                if document_text:
                    st.success(f"Extracted {len(document_text)} characters from document")
                    
                    # Show extracted text preview
                    with st.expander("View Extracted Text Preview"):
                        st.text_area("Extracted Text", document_text[:1000] + "..." if len(document_text) > 1000 else document_text, height=200)
                    
                    # Use AI to extract persona information
                    st.info("Using AI to extract persona information...")
                    persona_data = extract_persona_info_with_ai(document_text, persona_counter)
                    
                    if persona_data:
                        st.success("Persona information extracted!")
                        
                        # Display extracted information for review
                        st.subheader("Extracted Persona Information:")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**Name:** {persona_data['name']}")
                            age_display = persona_data.get('age') if persona_data.get('age') is not None else "Not specified"
                            st.write(f"**Age:** {age_display}")
                            st.write(f"**Job:** {persona_data['job']}")
                            st.write(f"**Education:** {persona_data['education']}")
                        
                        with col2:
                            st.write(f"**Personality:** {persona_data['personality']}")
                            # Opinions are kept for internal use but not displayed
                        
                        # Allow editing before saving
                        with st.expander("Edit Persona Information"):
                            edited_name = st.text_input("Name", value=persona_data['name'])
                            age_value = persona_data.get('age') if persona_data.get('age') is not None else 0
                            edited_age_input = st.number_input("Age (optional - 0 means not specified)", value=age_value, min_value=0, max_value=99)
                            edited_age = None if edited_age_input == 0 else edited_age_input
                            edited_job = st.text_input("Job", value=persona_data['job'])
                            edited_education = st.text_input("Education", value=persona_data['education'])
                            edited_personality = st.text_area("Personality", value=persona_data['personality'])
                            
                            if st.button("Update Persona Info"):
                                persona_data = {
                                    "name": edited_name,
                                    "age": edited_age,
                                    "job": edited_job,
                                    "education": edited_education,
                                    "personality": edited_personality,
                                    # Preserve original text and opinions
                                    "original_text": persona_data.get("original_text", ""),
                                    "opinions": persona_data.get("opinions", {})
                                }
                                st.success("Persona information updated!")
                        
                        # Save persona
                        if st.button("Save Persona"):
                            try:
                                validated_data = validate_persona_data(persona_data)
                                filename = f"personas/{validated_data['name'].lower().replace(' ', '_')}.json"
                                with open(filename, "w") as f:
                                    json.dump(validated_data, f, indent=2)
                                st.success("Persona saved")
                                st.session_state.personas.append(validated_data['name'])
                            except Exception as e:
                                st.error(f"Error saving persona: {str(e)}")
                    else:
                        st.error("Could not extract persona information from document")
                else:
                    st.error("Could not extract text from document")
                    
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
    
    else:  # Manual Entry
        st.subheader("Manual Persona Entry")
        st.info("Enter a description of the persona in the text box below. Click 'Analyze with AI' to extract the relevant information (name, age, job, education, personality, opinions, etc.).")
        
        # Initialize session state for manual persona entry
        if 'manual_persona_text' not in st.session_state:
            st.session_state.manual_persona_text = ""
        if 'manual_persona_data' not in st.session_state:
            st.session_state.manual_persona_data = None
        
        # Text input for persona description
        persona_text = st.text_area(
            "Enter persona description:",
            value=st.session_state.manual_persona_text,
            height=200,
            placeholder="Example: John is a 35-year-old software engineer with a Master's degree in Computer Science. He is analytical, detail-oriented, and values work-life balance. He is cautiously optimistic about AI technology and believes it will augment human capabilities rather than replace them. He enjoys remote work for its flexibility but also values occasional in-person collaboration."
        )
        
        # Update session state
        st.session_state.manual_persona_text = persona_text
        
        # Analyze button - analyze when clicked (similar to document upload flow)
        if persona_text.strip():
            if st.button("Analyze with AI"):
                try:
                    # Get persona counter for naming
                    persona_counter = len(existing_personas) + 1
                    
                    # Use AI to extract persona information
                    with st.spinner("Using AI to extract persona information..."):
                        persona_data = extract_persona_info_with_ai(persona_text, persona_counter)
                    
                    if persona_data:
                        st.session_state.manual_persona_data = persona_data
                        st.success("Persona information extracted!")
                        st.rerun()
                    else:
                        st.error("Could not extract persona information. Please try again with more details.")
                except Exception as e:
                    st.error(f"Error analyzing persona: {str(e)}")
        else:
            st.info("Enter a persona description above, then click 'Analyze with AI' to extract information.")
        
        # Display extracted information if available
        if st.session_state.manual_persona_data:
            persona_data = st.session_state.manual_persona_data
            
            st.subheader("Extracted Persona Information:")
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Name:** {persona_data['name']}")
                age_display = persona_data.get('age') if persona_data.get('age') is not None else "Not specified"
                st.write(f"**Age:** {age_display}")
                st.write(f"**Job:** {persona_data['job']}")
                st.write(f"**Education:** {persona_data['education']}")
            
            with col2:
                st.write(f"**Personality:** {persona_data['personality']}")
                # Opinions are kept for internal use but not displayed
            
            # Allow editing before saving
            with st.expander("Edit Persona Information"):
                edited_name = st.text_input("Name", value=persona_data['name'], key="edit_name")
                age_value = persona_data.get('age') if persona_data.get('age') is not None else 30
                edited_age = st.number_input("Age (optional)", value=age_value, min_value=18, max_value=99, key="edit_age")
                if edited_age == 30 and persona_data.get('age') is None:
                    edited_age = None
                edited_job = st.text_input("Job", value=persona_data['job'], key="edit_job")
                edited_education = st.text_input("Education", value=persona_data['education'], key="edit_education")
                edited_personality = st.text_area("Personality", value=persona_data['personality'], key="edit_personality")
                
                if st.button("Update Persona Info", key="update_manual"):
                    persona_data = {
                        "name": edited_name,
                        "age": edited_age,
                        "job": edited_job,
                        "education": edited_education,
                        "personality": edited_personality,
                        # Preserve original text and opinions
                        "original_text": persona_data.get("original_text", ""),
                        "opinions": persona_data.get("opinions", {})
                    }
                    st.session_state.manual_persona_data = persona_data
                    st.success("Persona information updated!")
                    st.rerun()
            
            # Save persona
            if st.button("Save Persona", key="save_manual"):
                try:
                    validated_data = validate_persona_data(st.session_state.manual_persona_data)
                    filename = f"personas/{validated_data['name'].lower().replace(' ', '_')}.json"
                    with open(filename, "w") as f:
                        json.dump(validated_data, f, indent=2)
                    st.success("Persona saved")
                    st.session_state.personas.append(validated_data['name'])
                    # Clear session state after saving
                    st.session_state.manual_persona_text = ""
                    st.session_state.manual_persona_data = None
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving persona: {str(e)}")

# --- Simulate Interviews --- #
with tab3:
    st.header("Simulate Interviews")
    
    # Show status of prerequisites
    col1, col2 = st.columns(2)
    with col1:
        # Try to sync questions from disk if session state is empty
        if not st.session_state.questions:
            _q_path = os.path.join("questions", "questions.txt")
            if os.path.exists(_q_path):
                try:
                    with open(_q_path, "r") as f:
                        st.session_state.questions = [line.strip() for line in f if line.strip()]
                except Exception:
                    pass

        if st.session_state.questions:
            st.success("Questions loaded")
        else:
            st.warning("Questions not loaded")
    
    with col2:
        persona_files = [f for f in os.listdir("personas") if f.endswith('.json')]
        if persona_files:
            st.success(f"{len(persona_files)} personas found")
        else:
            st.warning("No personas found")
    
    if not st.session_state.questions:
        st.warning("Please upload questions in Tab 1 first.")
    elif not persona_files:
        st.warning("Please create personas in Tab 2 first.")
    else:
        for persona_file in persona_files:
            persona_path = os.path.join("personas", persona_file)
            output_path = os.path.join("data", "ai_responses", persona_file.replace('.json', '_responses.json'))
            
            # Check if interview already exists
            interview_exists = os.path.exists(output_path)
            
            if interview_exists:
                st.info(f"Interview already exists for {persona_file.replace('.json', '')}")
                if st.button(f"Re-run Interview for {persona_file}"):
                    try:
                        simulate_interview(persona_path, os.path.join("questions", "questions.txt"), output_path)
                        st.success("Interview updated")
                        # Provide immediate download
                        try:
                            with open(output_path, 'rb') as f:
                                st.download_button(
                                    label=f"Download {persona_file.replace('.json','')}_responses.json",
                                    data=f,
                                    file_name=persona_file.replace('.json','_responses.json'),
                                    mime="application/json",
                                    key=f"download_responses_rerun_{persona_file}"
                                )
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Error simulating interview: {str(e)}")
            else:
                if st.button(f"Run Interview for {persona_file}"):
                    try:
                        simulate_interview(persona_path, os.path.join("questions", "questions.txt"), output_path)
                        st.success("Interview completed")
                        # Provide immediate download
                        try:
                            with open(output_path, 'rb') as f:
                                st.download_button(
                                    label=f"Download {persona_file.replace('.json','')}_responses.json",
                                    data=f,
                                    file_name=persona_file.replace('.json','_responses.json'),
                                    mime="application/json",
                                    key=f"download_responses_new_{persona_file}"
                                )
                        except Exception:
                            pass
                    except Exception as e:
                        st.error(f"Error simulating interview: {str(e)}")

# --- Compare & Analyze --- #
with tab4:
    st.header("Compare Real vs AI Interviews")
    st.info("**Purpose:** Compare your real interview transcript with AI-generated responses to analyze differences in themes, responses, and insights.")
    
    # Check for real interview transcript
    real_transcript_path = os.path.join("data", "real_interview_transcript.txt")
    real_transcript_exists = os.path.exists(real_transcript_path)
    
    # Check for AI responses
    response_files = sorted([f for f in os.listdir(os.path.join("data", "ai_responses")) if f.endswith('.json')])
    
    # Create outputs directory if it doesn't exist
    os.makedirs("outputs", exist_ok=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if real_transcript_exists:
            st.success("Real interview transcript uploaded")
            # Add download button for real transcript
            with open(real_transcript_path, 'rb') as f:
                st.download_button(
                    label="Download Real Transcript",
                    data=f,
                    file_name="real_interview_transcript.txt",
                    mime="text/plain",
                    key="download_real_transcript_tab4"
                )
        else:
            st.warning("No real interview transcript found")
    
    with col2:
        if response_files:
            st.success(f"{len(response_files)} AI interviews generated")
            
            # Add download dropdown for AI responses
            selected_ai_file = st.selectbox("Select AI interview to download:", response_files)
            ai_file_path = os.path.join("data", "ai_responses", selected_ai_file)
            
            with open(ai_file_path, 'rb') as f:
                st.download_button(
                    label=f"Download {selected_ai_file}",
                    data=f,
                    file_name=selected_ai_file,
                    mime="application/json",
                    key=f"download_ai_file_{selected_ai_file}"
                )
        else:
            st.warning("No AI interviews found")
    
    if real_transcript_exists and response_files:
        st.subheader("Analysis Options")
        
        selected_ai_file = st.selectbox("Choose AI interview to compare:", response_files)
        
        # Comparison analysis
        if st.button("Run Comparison Analysis"):
            try:
                # Load real transcript
                with open(real_transcript_path, 'r') as f:
                    real_transcript = f.read()
                
                # Load AI responses
                ai_responses_path = os.path.join("data", "ai_responses", selected_ai_file)
                with open(ai_responses_path, 'r') as f:
                    ai_responses = json.load(f)
                
                # Create comparison analysis using AI
                client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
                
                ai_text = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in ai_responses])
                
                comparison_prompt = f"""
                Using the Gioia methodology, compare the real interview transcript to the AI-generated responses.
                
                Produce:
                - First-order concepts (codes) with representative quotes for BOTH real and AI.
                - Second-order themes grouping those codes.
                - Aggregate dimensions summarizing the themes.
                - A side-by-side matrix highlighting differences between Real vs AI for each theme/dimension.
                - A concise discussion of where AI lacks or exceeds human depth, authenticity, and emotional nuance.
                
                Real Interview Transcript (excerpt):
                {real_transcript[:2000]}
                
                AI-Generated Responses (excerpt):
                {ai_text[:2000]}
                
                Return structured Markdown with clear sections and tables where appropriate.
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are an expert qualitative researcher comparing real and AI-generated interview data."},
                        {"role": "user", "content": comparison_prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                comparison_analysis = response.choices[0].message.content
                
                # Save comparison (internal) and provide download
                comparison_path = os.path.join("outputs", f"comparison_analysis_{selected_ai_file.replace('.json', '')}.md")
                with open(comparison_path, 'w') as f:
                    f.write(f"# Real vs AI Interview Comparison Analysis (Gioia)\n\n")
                    f.write(f"**AI Interview File:** {selected_ai_file}\n\n")
                    f.write(comparison_analysis)
                st.success("Comparison analysis generated")
                st.download_button(
                    label="Download Comparison Analysis",
                    data=f"# Real vs AI Interview Comparison Analysis (Gioia)\n\n**AI Interview File:** {selected_ai_file}\n\n" + comparison_analysis,
                    file_name=f"comparison_analysis_{selected_ai_file.replace('.json','')}.md",
                    mime="text/markdown",
                    key=f"download_comparison_{selected_ai_file.replace('.json','')}"
                )
                
                # Display analysis
                st.subheader("Comparison Analysis Results")
                st.markdown(comparison_analysis)
                
            except Exception as e:
                st.error(f"Error running comparison analysis: {str(e)}")
        
        # Individual analysis options
        st.subheader("Individual Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Real Interview Analysis**")
            if st.button("Analyze Real Interview"):
                try:
                    with open(real_transcript_path, 'r') as f:
                        real_transcript = f.read()
                    
                    # Create analysis of real interview
                    real_analysis_path = os.path.join("outputs", "real_interview_analysis.md")
                    
                    client = openai.OpenAI(api_key=get_secret("OPENAI_API_KEY"))
                    
                    real_analysis_prompt = f"""
                    Analyze this real interview transcript using the Gioia methodology:
                    1. Identify 3 aggregate dimensions
                    2. Find 3 themes under each dimension  
                    3. Extract 3-5 first-order codes under each theme
                    4. Include representative quotes for each code
                    
                    Interview Transcript:
                    {real_transcript[:3000]}
                    """
                    
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "You are an expert qualitative researcher using the Gioia methodology."},
                            {"role": "user", "content": real_analysis_prompt}
                        ],
                        max_tokens=2000,
                        temperature=0.3
                    )
                    
                    real_analysis = response.choices[0].message.content
                    
                    with open(real_analysis_path, 'w') as f:
                        f.write(f"# Real Interview Gioia Analysis\n\n")
                        f.write(real_analysis)
                    st.success("Real interview analysis generated")
                    st.download_button(
                        label="Download Real Interview Analysis",
                        data=f"# Real Interview Gioia Analysis\n\n" + real_analysis,
                        file_name="real_interview_gioia_analysis.md",
                        mime="text/markdown",
                        key="download_real_interview_analysis"
                    )
                    
                except Exception as e:
                    st.error(f"Error analyzing real interview: {str(e)}")
        
        with col2:
            st.write("**AI Interview Analysis**")
            if st.button("Analyze AI Interview"):
                try:
                    ai_analysis_path = os.path.join("outputs", selected_ai_file.replace('.json', '_gioia.md'))
                    analyze_gioia(os.path.join("data", "ai_responses", selected_ai_file), ai_analysis_path)
                    st.success("AI interview analysis generated")
                    try:
                        with open(ai_analysis_path, 'rb') as f:
                            st.download_button(
                                label="Download AI Interview Gioia Analysis",
                                data=f,
                                file_name=os.path.basename(ai_analysis_path),
                                mime="text/markdown",
                                key=f"download_ai_gioia_{selected_ai_file.replace('.json','')}"
                            )
                    except Exception:
                        pass
                except Exception as e:
                    st.error(f"Error analyzing AI interview: {str(e)}")
        
        # Enhanced Export Options
        st.subheader("Export & Download Options")
        
        # Create export directory if it doesn't exist
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        
        # Comparison Analysis Export
        st.markdown("### Comparison Analysis")
        comparison_files = sorted([f for f in os.listdir("outputs") if f.startswith("comparison_analysis")])
        
        if comparison_files:
            st.success(f"Found {len(comparison_files)} comparison analyses")
            
            # Download button for each comparison file
            for comp_file in comparison_files:
                comp_path = os.path.join("outputs", comp_file)
                with open(comp_path, 'rb') as f:
                    st.download_button(
                        label=f"Download {comp_file}",
                        data=f,
                        file_name=comp_file,
                        mime="text/markdown",
                        key=f"download_comp_{comp_file}"
                    )
        else:
            st.warning("No comparison analyses found. Run the comparison first.")
        
        # Gioia Analysis Export
        st.markdown("### Gioia Analysis")
        gioia_files = sorted([f for f in os.listdir("outputs") if "_gioia." in f])
        
        if gioia_files:
            st.success(f"Found {len(gioia_files)} Gioia analyses")
            
            # Download button for each Gioia analysis
            for gioia_file in gioia_files:
                gioia_path = os.path.join("outputs", gioia_file)
                with open(gioia_path, 'rb') as f:
                    st.download_button(
                        label=f"Download {gioia_file}",
                        data=f,
                        file_name=gioia_file,
                        mime="text/markdown",
                        key=f"download_gioia_{gioia_file}"
                    )
        else:
            st.warning("No Gioia analyses found. Run the analysis first.")
        
        # AI Interview Export
        st.markdown("### AI Interview Export")
        if selected_ai_file:
            col1, col2 = st.columns(2)
            
            with col1:
                # Export to DOCX
                if st.button("Export to DOCX"):
                    try:
                        input_path = os.path.join("data", "ai_responses", selected_ai_file)
                        base_name = selected_ai_file.replace('.json', '')
                        export_path = os.path.join(export_dir, f"{base_name}.docx")
                        export_both(input_path, base_name, output_dir=export_dir)
                        st.success(f"Exported to {export_path}")
                        
                        # Provide download link
                        with open(export_path, 'rb') as f:
                            st.download_button(
                                label="Download DOCX",
                                data=f,
                                file_name=f"{base_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"download_docx_{base_name}"
                            )
                    except Exception as e:
                        st.error(f"Error exporting to DOCX: {str(e)}")
            
            with col2:
                # Export to PDF
                if st.button("Export to PDF"):
                    try:
                        input_path = os.path.join("data", "ai_responses", selected_ai_file)
                        base_name = selected_ai_file.replace('.json', '')
                        pdf_path = os.path.join(export_dir, f"{base_name}.pdf")
                        export_both(input_path, base_name, output_dir=export_dir)
                        
                        # Provide download link
                        with open(pdf_path, 'rb') as f:
                            st.download_button(
                                label="Download PDF",
                                data=f,
                                file_name=f"{base_name}.pdf",
                                mime="application/pdf",
                                key=f"download_pdf_{base_name}"
                            )
                    except Exception as e:
                        st.error(f"Error exporting to PDF: {str(e)}")
    
    else:
        st.warning("Please upload a real interview transcript (Tab 1) and generate AI interviews (Tab 3) to enable comparison analysis.")

