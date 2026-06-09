import React, { useState, useEffect, useRef } from 'react';
import { api, ChatSummary, ChatTurn } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import DesmosGraph from './DesmosGraph';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { v4 as uuidv4 } from 'uuid';
import { Plus, Trash2, MessageSquare, LineChart } from 'lucide-react';

const ChatInterface: React.FC = () => {
  const [chats, setChats] = useState<ChatSummary[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string>(uuidv4());
  const [messages, setMessages] = useState<ChatTurn[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<Record<number, 'explanation' | 'graph'>>({});

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadChats();
  }, []);

  useEffect(() => {
    if (currentChatId) {
      loadHistory(currentChatId);
    }
  }, [currentChatId]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const loadChats = async () => {
    try {
      const data = await api.getChats();
      setChats(data);
    } catch (err) {
      console.error(err);
    }
  };

  const loadHistory = async (id: string) => {
    try {
      const history = await api.getChatHistory(id);
      setMessages(history);
      // Initialize tabs for history
      const newTabs: Record<number, 'explanation' | 'graph'> = {};
      history.forEach((msg, i) => {
        if (msg.plot_equation) {
          newTabs[i] = 'explanation';
        }
      });
      setActiveTab(newTabs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputValue.trim() || isLoading) return;

    const userMsg = inputValue;
    setInputValue('');
    setIsLoading(true);

    // Optimistic update
    const newMessages = [...messages, { user: userMsg, bot: 'Thinking...' }];
    setMessages(newMessages);

    try {
      const response = await api.sendMessage(currentChatId, userMsg);
      const updatedMessages = [...messages, { 
        user: userMsg, 
        bot: response.bot_response, 
        plot_equation: response.plot_equations || undefined 
      }];
      setMessages(updatedMessages);
      
      if (response.plot_equations) {
        setActiveTab(prev => ({ ...prev, [updatedMessages.length - 1]: 'explanation' }));
      }
      
      loadChats(); // Refresh sidebar titles
    } catch (err) {
      console.error(err);
      setMessages([...messages, { user: userMsg, bot: 'Error: Failed to get response.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    const newId = uuidv4();
    setCurrentChatId(newId);
    setMessages([]);
    setActiveTab({});
  };

  const handleDeleteChat = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deleteChat(id);
      loadChats();
      if (currentChatId === id) {
        startNewChat();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      {/* Sidebar */}
      <div className="w-64 border-r flex flex-col p-4 space-y-4 overflow-hidden">
        <Button onClick={startNewChat} className="w-full">
          <Plus className="mr-2 h-4 w-4" /> New Chat
        </Button>
        <div className="flex-1 overflow-y-auto space-y-2">
          <p className="text-xs font-semibold text-muted-foreground uppercase px-2">Previous Conversations</p>
          {chats.map(chat => (
            <div 
              key={chat.id}
              onClick={() => setCurrentChatId(chat.id)}
              className={`flex items-center justify-between p-2 rounded-md cursor-pointer hover:bg-accent group ${currentChatId === chat.id ? 'bg-accent' : ''}`}
            >
              <div className="flex items-center overflow-hidden">
                <MessageSquare className="h-4 w-4 mr-2 flex-shrink-0" />
                <span className="truncate text-sm">{chat.title}</span>
              </div>
              <Trash2 
                className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive cursor-pointer" 
                onClick={(e) => handleDeleteChat(chat.id, e)}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="p-4 border-b flex justify-between items-center">
          <h1 className="text-xl font-bold">📘 AI Math Tutor</h1>
        </header>

        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="max-w-3xl mx-auto space-y-6 pb-12">
            {messages.length === 0 && (
              <div className="text-center py-20 space-y-4">
                <h2 className="text-2xl font-semibold">Welcome to AI Math Tutor!</h2>
                <p className="text-muted-foreground">Try asking a math question or entering an equation to graph.</p>
                <div className="flex flex-wrap justify-center gap-2">
                  {["y = x^2 - 4x + 3", "integrate sin(x) from 0 to pi dx", "x = 2t+1; y = t^2 - 3"].map(ex => (
                    <Button key={ex} variant="outline" size="sm" onClick={() => { setInputValue(ex); handleSendMessage(); }}>
                      {ex}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className="space-y-4">
                {/* User Message */}
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground p-3 rounded-lg max-w-[80%]">
                    {msg.user}
                  </div>
                </div>

                {/* Bot Message */}
                <div className="flex justify-start">
                  <div className="bg-muted p-4 rounded-lg w-full">
                    <div className="prose prose-slate dark:prose-invert max-w-none">
                      <ReactMarkdown 
                        remarkPlugins={[remarkMath]} 
                        rehypePlugins={[rehypeKatex]}
                      >
                        {msg.bot}
                      </ReactMarkdown>
                    </div>

                    {msg.plot_equation && msg.bot !== 'Thinking...' && (
                      <div className="mt-4 space-y-4">
                        <div className="flex space-x-2 border-b">
                          <button 
                            className={`pb-2 px-4 ${activeTab[i] === 'explanation' ? 'border-b-2 border-primary font-semibold' : 'text-muted-foreground'}`}
                            onClick={() => setActiveTab(prev => ({ ...prev, [i]: 'explanation' }))}
                          >
                            Explanation
                          </button>
                          <button 
                            className={`pb-2 px-4 flex items-center ${activeTab[i] === 'graph' ? 'border-b-2 border-primary font-semibold' : 'text-muted-foreground'}`}
                            onClick={() => setActiveTab(prev => ({ ...prev, [i]: 'graph' }))}
                          >
                            <LineChart className="h-4 w-4 mr-2" /> Graph
                          </button>
                        </div>
                        
                        {activeTab[i] === 'explanation' ? (
                          <p className="text-sm text-muted-foreground py-2">Above is the explanation. Switch to the Graph tab to visualize.</p>
                        ) : (
                          <DesmosGraph equations={msg.plot_equation} />
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>

        {/* Input Area */}
        <div className="p-4 border-t">
          <form onSubmit={handleSendMessage} className="max-w-3xl mx-auto flex space-x-2">
            <Input 
              placeholder="Ask a question or enter an equation..." 
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
              className="flex-1"
            />
            <Button type="submit" disabled={isLoading || !inputValue.trim()}>
              {isLoading ? 'Thinking...' : 'Send'}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
