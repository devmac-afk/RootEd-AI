import re
import os
from typing import List, Optional, Annotated
from typing_extensions import TypedDict

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.environ.get("GOOGLE_MODEL", "gemini-2.5-flash")
TEMPERATURE = float(os.environ.get("MODEL_TEMPERATURE", "0.4"))

def convert_to_desmos_syntax(equation: str) -> str:
    # Normalize trig exponent usage like sin^2(x) -> (sin(x))^2 for Desmos
    pattern = r"(sin|cos|tan|cot|sec|csc)\^([2-9]|\d{2,})\s*\((.*?)\)"
    replacement = r"(\1(\3))^\2"
    eq = re.sub(pattern, replacement, equation)
    
    # Ensure trig functions have backslashes for Desmos LaTeX
    trig_functions = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'arcsin', 'arccos', 'arctan']
    for func in trig_functions:
        eq = re.sub(rf"(?<!\\)\b{func}\b", rf"\\{func}", eq)

    # Common replacements (sqrt -> \sqrt{}, implicit pi keyword)
    eq = re.sub(r"sqrt\s*\((.*?)\)", r"\\sqrt{\1}", eq, flags=re.IGNORECASE)
    eq = re.sub(r"\bpi\b", r"\\pi", eq, flags=re.IGNORECASE)
    return eq

@tool
def plot_graph(equations: List[str]):
    """
    Use this tool to display a graphing calculator to the user.
    Provide a list of mathematical equations in standard LaTeX format.
    Examples:
    - ["y = x^2 + 2x + 1"]
    - ["x = 2t", "y = t^2"]
    - ["\\int_{0}^{\\pi} \\sin(x) dx"]
    """
    cleaned_equations = [convert_to_desmos_syntax(eq) for eq in equations]
    # In a LangGraph tool, we just return a status. 
    # The actual equations will be extracted from the tool call in the API layer.
    return f"Successfully queued {len(cleaned_equations)} equations for plotting."

# Define the state for the graph
class AgentState(MessagesState):
    # MessagesState already includes 'messages': Annotated[list[AnyMessage], add_messages]
    pass

# Initialize the model
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=TEMPERATURE)
tools = [plot_graph]
llm_with_tools = llm.bind_tools(tools)

# Define the nodes
def call_model(state: AgentState):
    system_prompt = SystemMessage(content=(
        "You are an encouraging, highly intuitive, and precise AI Math Tutor.\n"
        "Your mission is to help the student understand the core concept, solve the problem step-by-step, and build mathematical confidence.\n\n"
        "Structure your response using these clear sections:\n"
        "1. 💡 **Core Strategy**: Briefly explain the main mathematical concept/approach in 1-2 simple sentences before diving into calculations.\n"
        "2. 🔢 **Step-by-Step Solution**:\n"
        "   - Break down the solution into logical, numbered steps.\n"
        "   - For each step, explicitly name the rule, formula, or theorem used.\n"
        "   - Explain *why* you are making each algebraic step.\n"
        "3. 🎯 **Tutor Tip**: Provide a quick, general pattern or shortcut.\n"
        "4. 📈 **Graphing Note**: If you have called the plot_graph tool, describe exactly what they should look for on the graph.\n\n"
        "Formatting & Tone Rules:\n"
        "- Use inline LaTeX with single $ for variables and short terms.\n"
        "- Use block LaTeX with double $$ for standalone equations.\n"
        "- Keep the tone supportive and collaborative.\n"
        "- If a question involves visualization or graphing, ALWAYS use the plot_graph tool."
    ))
    
    # Prepend system prompt to the conversation
    messages = [system_prompt] + state['messages']
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# Define the graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

workflow.set_entry_point("agent")

# Define conditional edges
def should_continue(state: AgentState):
    messages = state['messages']
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

workflow.add_conditional_edges(
    "agent",
    should_continue,
)

workflow.add_edge("tools", "agent")

# Compile the graph
app = workflow.compile()
