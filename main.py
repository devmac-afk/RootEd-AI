import streamlit as st

# --- 1. SET PAGE CONFIG (MUST BE FIRST) ---
st.set_page_config(page_title="AI Math Tutor", layout="wide")

# --- 2. ALL OTHER IMPORTS ---
import uuid
import re
import os
from typing import List, Optional, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

from desmos_component import show_desmos
from supabase_client import save_chat, load_chat, delete_chat, get_all_chat_summaries

# --- 3. LOAD ENVIRONMENT VARIABLES & API KEYS ---
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    st.error("GOOGLE_API_KEY not found. Please add it to your .env file.")
    st.stop()

MODEL_NAME = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0.4"))

# --- 4. HELPER FUNCTIONS ---
def generalize_expression_to_function(expression: str) -> Optional[str]:
    number_pattern = r"(?<!\^)\b\d+(\.\d+)?\b"
    first_number_match = re.search(number_pattern, expression)
    if not first_number_match:
        return None
    number_to_replace = first_number_match.group(0)
    trig_functions = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc']
    is_trigonometric = any(func in expression.lower() for func in trig_functions)
    if is_trigonometric:
        variable = "\\theta"
        generalized_expr = expression.replace(number_to_replace, variable)
        return f"r = {generalized_expr}"
    else:
        variable = "x"
        generalized_expr = expression.replace(number_to_replace, variable)
        return f"y = {generalized_expr}"

def convert_to_desmos_syntax(equation: str) -> str:
    # Normalize trig exponent usage like sin^3(x) -> (sin(x))^3 for Desmos
    pattern = r"(sin|cos|tan|cot|sec|csc)\^([3-9]|\d{2,})\s*\((.*?)\)"
    replacement = r"(\1(\3))^\2"
    eq = re.sub(pattern, replacement, equation)
    # Common replacements (sqrt -> \sqrt{}, implicit pi keyword)
    eq = re.sub(r"sqrt\s*\((.*?)\)", r"\\sqrt{\1}", eq, flags=re.IGNORECASE)
    eq = re.sub(r"\bpi\b", r"\\pi", eq, flags=re.IGNORECASE)
    return eq

def extract_plottable_equation(user_query: str) -> Optional[List[str]]:
    original_query = user_query.strip()

    # Definite integral patterns: "integrate f(x) from a to b dx" or "integrate a to b f(x) dx"
    match_A = re.search(r"integrate\s+(.*?)\s+to\s+(.*?)\s+(.*?)\s*d([xytzθ])", original_query, re.IGNORECASE)
    match_B = re.search(r"integrate\s+(.*?)\s+from\s+(.*?)\s+to\s+(.*?)\s*d([xytzθ])", original_query, re.IGNORECASE)
    lower_limit, upper_limit, function_part, integration_variable = None, None, None, None
    if match_A:
        lower_limit, upper_limit, function_part, integration_variable = match_A.groups()
    elif match_B:
        function_part, lower_limit, upper_limit, integration_variable = match_B.groups()
    if function_part:
        def translate_pi(text):
            return re.sub(r'\b(pi|pie)\b', r'\\pi', text, flags=re.IGNORECASE)
        lower_limit = translate_pi(lower_limit.strip())
        upper_limit = translate_pi(upper_limit.strip())
        cleaned_function = translate_pi(function_part.strip())
        if integration_variable.lower() == 'θ':
            integration_variable = r'\theta'
        assignment_variable = 'r' if integration_variable == r'\theta' else 'y'
        integral_expression = f"\\int_{{{lower_limit}}}^{{{upper_limit}}} ({cleaned_function}) d{integration_variable}"
        final_equation = f"{assignment_variable} = {integral_expression}"
        return [final_equation]

    cleaned_query = re.sub(r"^(solve|plot|graph|what is|can you solve|show)\s*:?\s*", "", original_query, flags=re.IGNORECASE)
    if not cleaned_query:
        return None

    # Avoid derivatives for now
    if re.search(r"(dy/dx|y\'|d/dx)", cleaned_query):
        return None

    # Parametric detection
    if 't' in cleaned_query.lower():
        parametric_match = re.search(r"x\s*=\s*(.*?),?\s*y\s*=\s*(.*)", cleaned_query, re.IGNORECASE)
        if parametric_match:
            return [f"({parametric_match.group(1).strip()}, {parametric_match.group(2).strip()})"]

    # Multiple equations split by semicolon or newline
    parts = re.split(r"[;\n]+", cleaned_query)
    equations: List[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '=' in part and any(v in part.lower() for v in ['x', 'y', 'r']):
            equations.append(part)
            continue
        if any(op in part for op in ['+', '-', '*', '/', '^']):
            if r'\theta' in part or 'theta' in part.lower():
                equations.append(f"r = {part}")
            elif re.search(r"\bx\b|\by\b", part, re.IGNORECASE):
                equations.append(f"y = {part}")
            else:
                generalized = generalize_expression_to_function(part)
                if generalized:
                    equations.append(generalized)
    return equations if equations else None

# --- 5. LLM AND MEMORY SETUP ---
@st.cache_resource
def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            (
                "You are an encouraging, highly intuitive, and precise AI Math Tutor.\n"
                "Your mission is to help the student understand the core concept, solve the problem step-by-step, and build mathematical confidence.\n\n"
                "Structure your response using these clear sections:\n"
                "1. 💡 **Core Strategy**: Briefly explain the main mathematical concept/approach in 1-2 simple sentences before diving into calculations.\n"
                "2. 🔢 **Step-by-Step Solution**:\n"
                "   - Break down the solution into logical, numbered steps.\n"
                "   - For each step, explicitly name the rule, formula, or theorem used (e.g., 'Using the Power Rule of Integration...', 'Applying the Quadratic Formula...').\n"
                "   - Explain *why* you are making each algebraic step (not just *what* the step is).\n"
                "3. 🎯 **Tutor Tip**: Provide a quick, general pattern or shortcut that helps them solve similar types of problems in the future.\n"
                "4. 📈 **Graphing Note** (only if the query involves plotting/graphing): Describe exactly what they should look for on the graph (e.g., key features like x/y intercepts, vertex, asymptotes, symmetry, and domain/range).\n\n"
                "Formatting & Tone Rules:\n"
                "- Use inline LaTeX with single $ (e.g., $x$ or $f(x)$) for variables, numbers, and short terms inside sentences.\n"
                "- Use block LaTeX with double $$ (on separate lines) for standalone equations, steps, or the final result.\n"
                "- If the student seems confused or asks you to simplify, break down the step even further and use a simple, relatable real-world analogy.\n"
                "- Keep the tone supportive and collaborative (e.g., 'Let's work through this together step-by-step')."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=TEMPERATURE)
    memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    return LLMChain(llm=llm, prompt=prompt, memory=memory)

chain = get_chain()

# --- 6. MAIN APP LAYOUT AND LOGIC ---
st.title("📘 AI Math Tutor with Visualizer")
st.caption("Type an equation or a math question. I’ll solve it and, when applicable, show you the graph.")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_synced_chat_id" not in st.session_state:
    st.session_state.last_synced_chat_id = None

# Sync memory when the active chat changes
if st.session_state.last_synced_chat_id != st.session_state.chat_id:
    st.session_state.messages = load_chat(st.session_state.chat_id)
    chain.memory.clear()
    for turn in st.session_state.messages:
        if turn.get('user') and turn.get('bot'):
            chain.memory.chat_memory.add_user_message(turn.get('user'))
            chain.memory.chat_memory.add_ai_message(turn.get('bot'))
    st.session_state.last_synced_chat_id = st.session_state.chat_id

# Sidebar
with st.sidebar:
    st.title("Chats")
    if st.button("➕ New Chat", use_container_width=True):
        save_chat(st.session_state.chat_id, st.session_state.messages)
        st.session_state.chat_id = str(uuid.uuid4())
        st.session_state.last_synced_chat_id = None
        st.rerun()

    st.write("---")
    st.write("Previous Conversations:")
    all_chats = get_all_chat_summaries()
    unique_chats = []
    seen_ids = set()
    for chat in all_chats:
        if chat.get('id') and chat['id'] not in seen_ids:
            unique_chats.append(chat)
            seen_ids.add(chat['id'])
    for chat in unique_chats:
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(chat["title"], key=f"chat_{chat['id']}", use_container_width=True):
                save_chat(st.session_state.chat_id, st.session_state.messages)
                st.session_state.chat_id = chat["id"]
                st.session_state.last_synced_chat_id = None
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{chat['id']}", use_container_width=True):
                delete_chat(chat["id"])
                if st.session_state.chat_id == chat['id']:
                    st.session_state.chat_id = str(uuid.uuid4())
                    st.session_state.last_synced_chat_id = None
                st.rerun()

# Helpful examples when chat is empty
if not st.session_state.messages:
    st.info("Try one of these:")
    cols = st.columns(3)
    examples = [
        "y = x^2 - 4x + 3",
        "integrate sin(x) from 0 to pi dx",
        "x = 2t+1; y = t^2 - 3",
    ]
    for c, ex in zip(cols, examples):
        with c:
            if st.button(ex, use_container_width=True):
                st.session_state.messages.append({"user": ex, "bot": "Thinking..."})
                st.rerun()

# Stateful Chat Display Loop
for i, turn in enumerate(st.session_state.messages):
    with st.chat_message("user"):
        st.markdown(turn.get("user", ""))
    with st.chat_message("assistant"):
        st.markdown(turn.get("bot", ""))
        equations_to_plot: Union[None, str, List[str]] = turn.get("plot_equation")
        if equations_to_plot and turn.get("bot") != "Thinking...":
            tabs = st.tabs(["Explanation", "Graph"])
            with tabs[0]:
                st.markdown("Above is the explanation. Switch to the Graph tab to visualize.")
            with tabs[1]:
                if isinstance(equations_to_plot, list):
                    desmos_ready_equations = [convert_to_desmos_syntax(eq) for eq in equations_to_plot if eq]
                    show_desmos(desmos_ready_equations, index=i)
                elif isinstance(equations_to_plot, str):
                    desmos_ready_equation = convert_to_desmos_syntax(equations_to_plot)
                    show_desmos(desmos_ready_equation, index=i)

# --- INPUT HANDLING ---
user_query = st.chat_input("Ask a question or enter an equation...")
if user_query:
    st.session_state.messages.append({"user": user_query, "bot": "Thinking..."})
    st.rerun()

# --- LLM CALL & POST-PROCESSING ---
last_turn = st.session_state.messages[-1] if st.session_state.messages else None
if last_turn and last_turn["bot"] == "Thinking...":
    try:
        with st.spinner("Thinking..."):
            response = chain.invoke({"question": last_turn["user"]})
            bot_response = response.get('text', '').strip()
    except Exception as e:
        bot_response = (
            "I ran into an issue while solving that. Please try rephrasing the question or simplifying the expression.\n\n"
            f"Error: {e}"
        )
    equation_to_plot = extract_plottable_equation(last_turn["user"]) or None

    st.session_state.messages[-1]["bot"] = bot_response
    st.session_state.messages[-1]["plot_equation"] = equation_to_plot

    save_chat(st.session_state.chat_id, st.session_state.messages)
    st.rerun()
