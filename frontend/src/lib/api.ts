const API_BASE_URL = 'http://localhost:8000/api';

export type ChatSummary = {
  id: string;
  title: string;
}

export type ChatTurn = {
  user: string;
  bot: string;
  plot_equation?: string | string[];
}

export const api = {
  async getChats(): Promise<ChatSummary[]> {
    const res = await fetch(`${API_BASE_URL}/chats`);
    if (!res.ok) throw new Error('Failed to fetch chats');
    return res.json();
  },

  async getChatHistory(chatId: string): Promise<ChatTurn[]> {
    const res = await fetch(`${API_BASE_URL}/chats/${chatId}`);
    if (!res.ok) throw new Error('Failed to fetch chat history');
    return res.json();
  },

  async sendMessage(chatId: string, message: string): Promise<{ bot_response: string, plot_equations: string[] | null }> {
    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, message })
    });
    if (!res.ok) throw new Error('Failed to send message');
    return res.json();
  },

  async deleteChat(chatId: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/chats/${chatId}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error('Failed to delete chat');
  }
};
