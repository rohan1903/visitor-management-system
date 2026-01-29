import streamlit as st
import google.generativeai as genai 
import google.api_core.exceptions
import os 

# --- Configuration ---

# IMPORTANT: REPLACE THIS PLACEHOLDER WITH YOUR ACTUAL GEMINI API KEY
# A valid key is required for the application to function.
GOOGLE_API_KEY = "AIzaSyBzf7V1q3f5g_5czJDPqNiD7LpENyj6FEc" 
# Configure the Gemini client using the API key
genai.configure(api_key=GOOGLE_API_KEY)

# Official College Name
COLLEGE_NAME = "G. Narayanamma Institute of Technology and Science (for Women) (GNITS)"

# Verified and Structured Knowledge Base (The core of the bot's "training")
# **This is the section you modify to "train" the bot with new facts and locations.**
COLLEGE_DATA = f"""
The institution is the {COLLEGE_NAME} college, located in Shaikpet, Hyderabad – 500104.
The bot is a campus navigator providing information about campus blocks, departments, labs, and key facilities based on the current layout.

CAMPUS LAYOUT AND BLOCKS:

A-BLOCK (Administration and Principal's Office):
- Ground Floor: Main Reception and Student Affairs Desk.
- First Floor: Principal's Office, Administrative Wing, Governing Body Offices.
- Second Floor: Placement Cell, Seminar Hall 1.

B-BLOCK (Computer Science and IT Cluster):
- Ground Floor: Department Office for Computer Science and Engineering (CSE).
- First Floor: Programming Labs (General Purpose), IT Department Office.
- Second Floor: Specialized Labs for CSE (AI/ML) and CSE (Data Science), Faculty Cabins for the CSE cluster.
- All Computer Science related departments (CSE, IT, CSE-AI/ML, CSE-Data Science, CSE-CST) are located in B-Block.

C-BLOCK (Electronics and Electrical Cluster):
- Ground Floor: Department Office for Electronics and Communication Engineering (ECE).
- First Floor: Basic Electronics Lab, VLSI Lab, ECE Faculty Cabins.
- Second Floor: Electrical and Electronics Engineering (EEE) Department Office, Electronics and Telematics Engineering (ETE) Department Office, Electrical Machines Lab.
- C-Block houses all Electrical and Electronics related departments.

D-BLOCK (Basic Sciences and Auxiliary Departments):
- Ground Floor: Basic Sciences Department (Physics, Chemistry Labs).
- First Floor: Department of Humanities and Mathematics.
- Second Floor: Auxiliary Engineering Departments (Mechanical and Civil Engineering staff/labs).

CENTRAL FACILITIES:
- Central Library: A dedicated, separate building located near the main A-Block. It includes both physical collections and a Digital Library section.
- Canteen & Dining: Main cafeteria located centrally, providing food service to students and staff.
- Auditorium: Located near the main entrance, used for large academic and cultural events.
- Hostels: Separate Hostel Block managed by G. Pulla Reddy Charities Trust, located close to the campus.
- Health Center: Health care facilities are available within the campus/hostel area.
- Transport Office: Manages bus routes and transport facilities for students and staff.
"""

# --- Streamlit Setup ---
st.set_page_config(page_title=f"{COLLEGE_NAME} Navigator", page_icon="🎓")

# --- System Prompt Definition (The bot's instructions and persona) ---
SYSTEM_PROMPT = (
    f"You are the '{COLLEGE_NAME} Campus Navigator', a highly efficient, professional, and friendly college assistant chatbot."
    f"Your entire knowledge base is: {COLLEGE_DATA}. "
    "Your primary function is to answer queries related to the college's campus layout, block locations, department offices, lab names, and central facilities."
    "You MUST ONLY use the provided knowledge base data for location and facility information. Do not invent details or guess room numbers not explicitly listed."
    "If the answer is not in the provided data, politely state that the information is not in your database and ask them to focus on campus location inquiries."
    f"Introduce yourself as the '{COLLEGE_NAME} Campus Navigator' and always be concise and direct in your responses."
)

# --- Chatbot Initialization ---
if "chat" not in st.session_state:
    # Using gemini-2.5-flash for stability and speed
    model = genai.GenerativeModel('gemini-2.5-flash') 

    # Start the chat and immediately send the system prompt to set the context
    st.session_state.chat = model.start_chat(history=[
        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
        # Internal model response to the system prompt
        {"role": "model", "parts": [{"text": "Understood. Ready to assist with GNITS campus inquiries."}]} 
    ])
    
    # Initial message for display in the chat history
    initial_greeting = f"Hello! I am the **{COLLEGE_NAME} Campus Navigator**. Ask me anything about blocks, departments, labs, or facilities. How can I help you navigate the campus today? 🗺️"
    st.session_state.messages = [{"role": "assistant", "content": initial_greeting}]

# Ensure messages list is always initialized for page reloads
if "messages" not in st.session_state:
    initial_greeting = f"Hello! I am the **{COLLEGE_NAME} Campus Navigator**. Ask me anything about blocks, departments, labs, or facilities. How can I help you navigate the campus today? 🗺️"
    st.session_state.messages = [{"role": "assistant", "content": initial_greeting}]


# --- Page Header ---
st.markdown(
    f"""
    <h1 style="text-align: center; color: #8B5CF6;">{COLLEGE_NAME} Navigator 🎓</h1>
    <p style="text-align: center; font-size: 18px;">Your personal guide to blocks, labs, and facilities on the GNITS campus.</p>
    <hr style="border-color: #A78BFA;">
    """,
    unsafe_allow_html=True,
)

# --- Display Chat History ---
for message in st.session_state.messages:
    avatar_icon = "🤖" if message["role"] == "assistant" else "👤"
    with st.chat_message(message["role"], avatar=avatar_icon):
        st.markdown(message["content"])

# --- User Input and Response Generation ---
if prompt := st.chat_input("Ask about a department, lab location, or block number..."):
    # 1. Add user message to state and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    try:
        # 2. Send user message to the Gemini API
        response = st.session_state.chat.send_message(prompt)
        
        # 3. Display assistant response
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(response.text)

        # 4. Add assistant response to state
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except google.api_core.exceptions.InvalidArgument:
        error_msg = "Error: Invalid Gemini API key or configuration issue. Please check your key and ensure it is correct."
        with st.chat_message("assistant", avatar="⚠️"):
            st.markdown(error_msg)
        st.error(error_msg)
    except Exception as e:
        error_msg = "Something went wrong with the connection to the Gemini API. Please try again later."
        with st.chat_message("assistant", avatar="⚠️"):
            st.markdown(error_msg)
        st.error(f"An unexpected error occurred: {str(e)}")
