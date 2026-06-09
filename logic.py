import re
import os
from typing import List, Optional, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0.4"))

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

    # Definite integral patterns
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

    if re.search(r"(dy/dx|y\'|d/dx)", cleaned_query):
        return None

    if 't' in cleaned_query.lower():
        parametric_match = re.search(r"x\s*=\s*(.*?),?\s*y\s*=\s*(.*)", cleaned_query, re.IGNORECASE)
        if parametric_match:
            return [f"({parametric_match.group(1).strip()}, {parametric_match.group(2).strip()})"]

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
                "   - For each step, explicitly name the rule, formula, or theorem used.\n"
                "   - Explain *why* you are making each algebraic step.\n"
                "3. 🎯 **Tutor Tip**: Provide a quick, general pattern or shortcut.\n"
                "4. 📈 **Graphing Note** (only if the query involves plotting/graphing): Describe exactly what they should look for on the graph.\n\n"
                "Formatting & Tone Rules:\n"
                "- Use inline LaTeX with single $ for variables and short terms.\n"
                "- Use block LaTeX with double $$ for standalone equations.\n"
                "- Keep the tone supportive and collaborative."
            ),
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])
    llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=TEMPERATURE)
    memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
    return LLMChain(llm=llm, prompt=prompt, memory=memory)
