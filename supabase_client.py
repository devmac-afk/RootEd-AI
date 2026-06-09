# supabase_client.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv

def init_supabase_client():
    """
    Initializes and returns the Supabase client.
    """
    load_dotenv()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Supabase URL or Key is missing. Please check your .env file or environment variables.")
        return None

    try:
        client = create_client(url, key)
        print("Supabase client initialized successfully.")
        return client
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        return None

supabase = init_supabase_client()

def save_chat(chat_id, history):
    """Saves or updates the chat history for a given chat_id in Supabase."""
    if not history or not supabase:
        return None

    try:
        first_message = history[0].get('user', 'Untitled Chat')[:50]

        response = supabase.table('chat_history').upsert({
            'chat_id': chat_id,
            'history': history,
            'first_message': first_message,
            'updated_at': 'now()'
        }).execute()

        return response.data
    except Exception as e:
        print(f"Error saving chat to Supabase: {e}")
        return None

def load_chat(chat_id):
    """Loads the chat history for a given chat_id from Supabase."""
    if not supabase:
        return []

    try:
        response = supabase.table('chat_history').select('history').eq('chat_id', chat_id).limit(1).execute()

        if response.data:
            return response.data[0].get('history', [])

        return []
    except Exception as e:
        print(f"Error loading chat from Supabase: {e}")
        return []

def delete_chat(chat_id):
    """Deletes a chat session from Supabase."""
    if not supabase:
        return

    try:
        supabase.table('chat_history').delete().eq('chat_id', chat_id).execute()
    except Exception as e:
        print(f"Error deleting chat {chat_id}: {e}")

def get_all_chat_summaries():
    """Gets a summary of all chats (id and title) for the sidebar from Supabase."""
    if not supabase:
        return []

    try:
        response = supabase.table('chat_history').select('chat_id, first_message').order('updated_at', desc=True).execute()

        if response.data:
            return [{"id": row['chat_id'], "title": row['first_message']} for row in response.data]
        return []
    except Exception as e:
        print(f"Error getting chat summaries: {e}")
        return []