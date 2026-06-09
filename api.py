from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json

from logic import app as langgraph_app, convert_to_desmos_syntax
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from supabase_client import save_chat, load_chat, delete_chat, get_all_chat_summaries

app = FastAPI()

import os

# Enable CORS for the Astro frontend
allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    user: str
    bot: Optional[str] = None
    plot_equation: Optional[List[str]] = None

class ChatRequest(BaseModel):
    chat_id: str
    message: str

class ChatResponse(BaseModel):
    bot_response: str
    plot_equations: Optional[List[str]] = None

@app.get("/api/chats")
async def get_chats():
    return get_all_chat_summaries()

@app.get("/api/chats/{chat_id}")
async def get_chat_history(chat_id: str):
    history = load_chat(chat_id)
    return history

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Load history from Supabase and convert to LangChain messages
        history = load_chat(request.chat_id)
        messages = []
        for turn in history:
            if turn.get('user'):
                messages.append(HumanMessage(content=turn.get('user')))
            if turn.get('bot'):
                # Note: If we want to be very precise, we should reconstruct tool calls here too
                # but for most history, just the text bot response is enough for context.
                messages.append(AIMessage(content=turn.get('bot')))
        
        # 2. Add the new user message
        messages.append(HumanMessage(content=request.message))
        
        # 3. Invoke LangGraph
        config = {"configurable": {"thread_id": request.chat_id}}
        final_state = langgraph_app.invoke({"messages": messages}, config=config)
        
        # 4. Extract text response and plot equations
        # The text response is in the content of the LAST AIMessage
        # The plot equations are in the tool_calls of ANY of the AIMessages in the final state's turn
        bot_response = ""
        plot_equations = []
        
        # We iterate backwards to find the final text answer and all tool calls in the last exchange
        for msg in reversed(final_state['messages']):
            if isinstance(msg, AIMessage):
                if not bot_response and msg.content:
                    bot_response = msg.content
                if msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if tool_call['name'] == 'plot_graph':
                            # Apply desmos syntax conversion just in case, 
                            # though the tool already does it, it's safer to extract fresh
                            eqs = tool_call['args'].get('equations', [])
                            plot_equations.extend([convert_to_desmos_syntax(eq) for eq in eqs])
            
            # Stop once we hit the user message we just sent
            if isinstance(msg, HumanMessage) and msg.content == request.message:
                break

        # 5. Save to Supabase
        history.append({
            "user": request.message,
            "bot": bot_response,
            "plot_equation": plot_equations if plot_equations else None
        })
        save_chat(request.chat_id, history)
        
        return ChatResponse(
            bot_response=bot_response,
            plot_equations=plot_equations if plot_equations else None
        )
    except Exception as e:
        print(f"Error in chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chats/{chat_id}")
async def delete_chat_endpoint(chat_id: str):
    delete_chat(chat_id)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
