from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid

from logic import extract_plottable_equation, get_chain, convert_to_desmos_syntax
from supabase_client import save_chat, load_chat, delete_chat, get_all_chat_summaries

app = FastAPI()

# Enable CORS for the Astro frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
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

# Global dictionary to store LangChain chains per chat session
# Note: In a production app, you might want to use a more robust session management
chains = {}

def get_chat_chain(chat_id: str):
    if chat_id not in chains:
        chain = get_chain()
        # Load existing history from Supabase if available
        history = load_chat(chat_id)
        for turn in history:
            if turn.get('user') and turn.get('bot'):
                chain.memory.chat_memory.add_user_message(turn.get('user'))
                chain.memory.chat_memory.add_ai_message(turn.get('bot'))
        chains[chat_id] = chain
    return chains[chat_id]

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
        chain = get_chat_chain(request.chat_id)
        response = chain.invoke({"question": request.message})
        bot_response = response.get('text', '').strip()
        
        equations_to_plot = extract_plottable_equation(request.message)
        
        # Save to Supabase
        history = load_chat(request.chat_id)
        history.append({
            "user": request.message,
            "bot": bot_response,
            "plot_equation": equations_to_plot
        })
        save_chat(request.chat_id, history)
        
        return ChatResponse(
            bot_response=bot_response,
            plot_equations=equations_to_plot
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chats/{chat_id}")
async def delete_chat_endpoint(chat_id: str):
    delete_chat(chat_id)
    if chat_id in chains:
        del chains[chat_id]
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
