# supabase_client.py

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import streamlit as st

# It's good practice to make the client a singleton using Streamlit's cache
@st.cache_resource
def init_supabase_client():
    """
    Initializes and returns the Supabase client.
    Uses st.cache_resource to ensure only one client is created per session.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Fetch Supabase credentials from environment variables
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # Check if credentials are set
    if not url or not key:
        st.error("Supabase URL or Key is missing. Please check your .env file or environment variables.")
        return None

    try:
        # Create the Supabase client
        client = create_client(url, key)
        print("Supabase client initialized successfully.")
        return client
    except Exception as e:
        st.error(f"Error initializing Supabase client: {e}")
        return None

# Initialize the client. The functions below will use this global client object.
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
        st.error(f"Error saving chat to Supabase: {e}")
        return None

# In supabase_client.py, replace this one function

def load_chat(chat_id):
    """Loads the chat history for a given chat_id from Supabase."""
    if not supabase:
        return []

    try:
        # Use .limit(1) to be safe against accidental duplicates.
        # This will return a list of rows, so we get the first one.
        response = supabase.table('chat_history').select('history').eq('chat_id', chat_id).limit(1).execute()
        
        # The result is in response.data, which is a list.
        if response.data:
            # Get the first item from the list and then its 'history' key.
            return response.data[0].get('history', [])
        
        return [] # Return empty list if no data was found
    except Exception as e:
        # Now we can print the error because it's unexpected.
        st.error(f"Error loading chat from Supabase: {e}")
        return []

def delete_chat(chat_id):
    """Deletes a chat session from Supabase."""
    if not supabase:
        return

    try:
        supabase.table('chat_history').delete().eq('chat_id', chat_id).execute()
    except Exception as e:
        st.error(f"Error deleting chat {chat_id}: {e}")

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
        st.error(f"Error getting chat summaries: {e}")
        return []