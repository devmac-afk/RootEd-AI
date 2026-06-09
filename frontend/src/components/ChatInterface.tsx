import React, { useState, useEffect, useRef } from 'react';
import { api } from '@/lib/api';
import type { ChatSummary, ChatTurn } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import DesmosGraph from './DesmosGraph';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { v4 as uuidv4 } from 'uuid';
import { 
  Plus, Trash2, MessageSquare, LineChart, Send, 
  Sparkles, User, BrainCircuit, Terminal, 
  ChevronRight, BookOpen, Calculator, Command,
  Activity, Cpu, Database, Search, Code2,
  ChevronDown, ChevronUp, Loader2
} from 'lucide-react';

const ThinkingIndicator: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const allLogs = [
    "Analyzing semantic structure...",
    "Querying Gemini-2.5-Flash...",
    "Parsing LaTeX mappings...",
    "Computing logic steps...",
    "Optimizing constraints...",
    "Synthesizing response...",
    "Finalizing rendering..."
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentStep(prev => (prev < allLogs.length - 1 ? prev + 1 : prev));
    }, 800);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col space-y-2 animate-in fade-in slide-in-from-left-2 duration-300 max-w-sm">
      <div 
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center space-x-3 bg-white border border-slate-200 px-4 py-2 rounded-2xl shadow-sm cursor-pointer hover:bg-slate-50 transition-colors group"
      >
        <div className="relative flex items-center justify-center">
          <Loader2 className="h-4 w-4 text-primary animate-spin" />
          <BrainCircuit className="h-2 w-2 text-primary absolute" />
        </div>
        <div className="flex-1 min-w-[140px]">
          <p className="text-[12px] font-bold text-slate-700 leading-none">
            {allLogs[currentStep]}
          </p>
        </div>
        {isExpanded ? <ChevronUp className="h-3.5 w-3.5 text-slate-400" /> : <ChevronDown className="h-3.5 w-3.5 text-slate-400 group-hover:text-primary transition-colors" />}
      </div>
      
      {isExpanded && (
        <div className="bg-slate-900 rounded-xl p-4 shadow-xl border border-slate-800 font-mono text-[10px] space-y-1 animate-in zoom-in-95 duration-200">
          {allLogs.slice(0, currentStep + 1).map((log, i) => (
            <div key={i} className="flex items-center text-slate-400">
              <span className="text-emerald-500 mr-2 opacity-50">›</span>
              <span className={i === currentStep ? "text-emerald-400" : "opacity-70"}>{log}</span>
            </div>
          ))}
          <div className="h-1 w-1 bg-emerald-500 animate-pulse mt-1 ml-1" />
        </div>
      )}
    </div>
  );
};

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
  }, [messages, isLoading]);

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
      const newTabs: Record<number, 'explanation' | 'graph'> = {};
      history.forEach((msg, i) => {
        if (msg.plot_equation) {
          newTabs[i] = 'graph';
        }
      });
      setActiveTab(newTabs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (e?: React.FormEvent, overrideMsg?: string) => {
    if (e) e.preventDefault();
    const messageToSend = overrideMsg || inputValue;
    if (!messageToSend.trim() || isLoading) return;

    if (!overrideMsg) setInputValue('');
    setIsLoading(true);

    const prevMessages = [...messages];
    setMessages([...prevMessages, { user: messageToSend, bot: 'Thinking...' }]);

    try {
      const response = await api.sendMessage(currentChatId, messageToSend);
      const updatedMessages = [...prevMessages, { 
        user: messageToSend, 
        bot: response.bot_response, 
        plot_equation: response.plot_equations || undefined 
      }];
      setMessages(updatedMessages);
      
      if (response.plot_equations) {
        setActiveTab(prev => ({ ...prev, [updatedMessages.length - 1]: 'graph' }));
      }
      
      loadChats();
    } catch (err) {
      console.error(err);
      setMessages([...prevMessages, { user: messageToSend, bot: '### ⚠️ [CRITICAL_SYSTEM_ERROR]\n\nLink to RootEd Intelligence Core severed. Check console logs.' }]);
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
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden font-sans selection:bg-accent/30">
      {/* Sidebar */}
      <div className="w-80 border-r bg-muted/30 flex flex-col p-8 space-y-8 hidden lg:flex">
        <div className="flex items-center space-x-3">
          <div className="bg-primary shadow-lg shadow-primary/20 p-2 rounded-xl">
            <Terminal className="h-6 w-6 text-primary-foreground" />
          </div>
          <div>
            <span className="text-xl font-black tracking-tighter block leading-none">ROOTED</span>
            <span className="text-[10px] font-bold tracking-[0.2em] text-primary/80 leading-none">INTELLIGENCE</span>
          </div>
        </div>

        <Button onClick={startNewChat} className="w-full justify-start rounded-2xl h-12 font-bold transition-all hover:scale-[1.02] active:scale-95 shadow-lg shadow-primary/10">
          <Plus className="mr-2 h-4 w-4" /> New Worksheet
        </Button>

        <div className="flex-1 overflow-y-auto space-y-2 -mx-2 px-2 scrollbar-hide">
          <div className="flex items-center justify-between px-3 mb-4">
            <p className="text-[10px] font-black text-muted-foreground/60 uppercase tracking-widest flex items-center">
              <BookOpen className="h-3 w-3 mr-1.5" /> History
            </p>
          </div>
          {chats.map(chat => (
            <div 
              key={chat.id}
              onClick={() => setCurrentChatId(chat.id)}
              className={`flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition-all duration-300 group relative ${currentChatId === chat.id ? 'bg-white shadow-xl shadow-black/5 ring-1 ring-black/5' : 'hover:bg-white/50 text-muted-foreground'}`}
            >
              {currentChatId === chat.id && (
                <div className="absolute left-0 w-1 h-6 bg-primary rounded-full" />
              )}
              <div className="flex items-center overflow-hidden">
                <span className={`text-sm font-semibold truncate ${currentChatId === chat.id ? 'text-foreground' : ''}`}>
                  {chat.title}
                </span>
              </div>
              <Trash2 
                className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-all hover:text-destructive" 
                onClick={(e) => handleDeleteChat(chat.id, e)}
              />
            </div>
          ))}
        </div>
        
        <div className="p-4 bg-primary/5 rounded-2xl border border-primary/10 space-y-4">
          <div className="flex items-center text-[10px] font-bold text-primary uppercase tracking-tighter">
            <Database className="h-3 w-3 mr-1.5" /> System Metrics
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-[9px] font-bold text-muted-foreground uppercase">
              <span>Logic Depth</span>
              <span className="text-primary">98.4%</span>
            </div>
            <div className="w-full bg-slate-200 h-1 rounded-full overflow-hidden">
              <div className="bg-primary h-full w-[98%]" />
            </div>
          </div>
          <p className="text-[11px] text-muted-foreground leading-relaxed font-medium">
            Core G2.5-F stabilized. Ready for recursive parsing.
          </p>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col relative h-full bg-[#FAFBFF]">
        {/* Header */}
        <header className="h-20 border-b flex items-center justify-between px-10 bg-white/60 backdrop-blur-xl z-20 sticky top-0 border-white/40">
          <div className="flex items-center space-x-3 lg:hidden">
            <Terminal className="h-6 w-6 text-primary" />
            <span className="font-black text-xl tracking-tighter">ROOTED</span>
          </div>
          <div className="hidden lg:flex items-center space-x-2 text-sm font-bold text-muted-foreground/80">
            <Calculator className="h-4 w-4" />
            <span>Academic Processor</span>
            <ChevronRight className="h-4 w-4" />
            <span className="text-foreground tracking-tight">{chats.find(c => c.id === currentChatId)?.title || "Undefined Worksheet"}</span>
          </div>
          <div className="flex items-center bg-accent/10 px-4 py-1.5 rounded-full border border-accent/20">
            <div className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] mr-2.5"></div>
            <span className="text-[10px] font-black uppercase tracking-[0.15em] text-emerald-600/80">Core Stable</span>
          </div>
        </header>

        {/* Scrollable Container */}
        <div className="flex-1 overflow-y-auto scroll-smooth py-12" ref={scrollRef}>
          <div className="max-w-4xl mx-auto px-8 space-y-12">
            
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-center animate-in fade-in zoom-in duration-1000">
                <div className="relative mb-8">
                  <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full"></div>
                  <BrainCircuit className="h-20 w-20 text-primary relative z-10 animate-float" />
                </div>
                <h2 className="text-4xl font-black tracking-tight mb-4 text-slate-900">Logic. Visuals. Clarity.</h2>
                <p className="text-slate-500 text-lg font-medium max-w-lg mb-12 leading-relaxed">
                  Deeply analyze mathematical structures with the RootEd Intelligence Engine.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-2xl">
                  {[
                    { label: "Function Analysis", query: "y = x^2 - 4x + 3", icon: <LineChart className="h-4 w-4" /> },
                    { label: "Definite Integral", query: "integrate sin(x) from 0 to pi dx", icon: <Search className="h-4 w-4" /> },
                    { label: "Motion Physics", query: "x = 2t+1; y = t^2 - 3", icon: <Code2 className="h-4 w-4" /> }
                  ].map(ex => (
                    <button 
                      key={ex.label}
                      onClick={() => handleSendMessage(undefined, ex.query)}
                      className="p-6 bg-white rounded-3xl border border-slate-200 hover:border-primary hover:shadow-xl hover:shadow-primary/5 transition-all text-left group flex flex-col justify-between h-40"
                    >
                      <div className="bg-slate-50 p-2 rounded-xl self-start group-hover:bg-primary/10 group-hover:text-primary transition-colors">
                        {ex.icon}
                      </div>
                      <div>
                        <span className="block text-primary text-[10px] font-black uppercase tracking-widest mb-1">{ex.label}</span>
                        <span className="text-slate-600 font-mono text-[11px] leading-relaxed line-clamp-2">{ex.query}</span>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col space-y-6 ${msg.user ? 'items-end' : 'items-start'}`}>
                {/* User Message */}
                {msg.user && (
                  <div className="flex flex-col items-end space-y-2 max-w-[80%]">
                    <div className="flex items-center space-x-2 mr-2">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Input Vector</span>
                    </div>
                    <div className="bg-slate-900 text-white px-7 py-4 rounded-3xl rounded-tr-none shadow-2xl shadow-slate-200 text-sm font-medium leading-relaxed tracking-tight">
                      {msg.user}
                    </div>
                  </div>
                )}

                {/* AI Response */}
                <div className="w-full flex flex-col space-y-3 animate-in fade-in slide-in-from-left-4 duration-500">
                  <div className="flex items-center space-x-2 ml-4">
                    <Sparkles className="h-4 w-4 text-emerald-500" />
                    <span className="text-[10px] font-black text-emerald-600 uppercase tracking-[0.2em]">Solution Process</span>
                  </div>
                  
                  <div className="knowledge-card">
                    <div className="prose prose-academic max-w-none">
                      <ReactMarkdown 
                        remarkPlugins={[remarkMath]} 
                        rehypePlugins={[rehypeKatex]}
                        components={{
                          h1: ({node, ...props}) => <h1 className="text-2xl font-black mb-6 flex items-center" {...props} />,
                          h2: ({node, ...props}) => <h2 className="text-xl font-bold mt-10 mb-4 text-slate-800" {...props} />,
                          p: ({node, ...props}) => <p className="mb-5" {...props} />,
                          strong: ({node, ...props}) => <span className="font-black text-primary border-b-2 border-primary/20 pb-0.5" {...props} />,
                          div: ({node, className, children, ...props}) => {
                            if (className?.includes('math-display')) {
                              return <div className="math-font bg-primary/5 border-l-4 border-primary p-8 my-8 rounded-2xl shadow-inner text-xl overflow-x-auto" {...props}>{children}</div>
                            }
                            return <div className={className} {...props}>{children}</div>
                          },
                          code: ({node, inline, ...props}) => 
                            inline 
                              ? <code className="bg-slate-100 px-1.5 py-0.5 rounded-md text-slate-800 font-mono text-[13px] border border-slate-200" {...props} />
                              : <code className="block bg-slate-900 text-slate-300 p-6 rounded-2xl font-mono text-sm overflow-x-auto shadow-2xl my-6" {...props} />
                        }}
                      >
                        {msg.bot}
                      </ReactMarkdown>
                    </div>

                    {msg.plot_equation && msg.bot !== 'Thinking...' && (
                      <div className="mt-12 pt-8 border-t border-slate-100">
                        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                          <div className="inline-flex bg-slate-100/50 p-1.5 rounded-2xl border border-slate-200 shadow-inner">
                            <button 
                              className={`py-2 px-6 rounded-xl text-[11px] font-black transition-all ${activeTab[i] === 'explanation' ? 'bg-white text-primary shadow-lg shadow-black/5 ring-1 ring-black/5' : 'text-slate-400 hover:text-slate-600'}`}
                              onClick={() => setActiveTab(prev => ({ ...prev, [i]: 'explanation' }))}
                            >
                              <BookOpen className="h-3 w-3 inline mr-2 opacity-50" /> LOGIC
                            </button>
                            <button 
                              className={`py-2 px-6 rounded-xl text-[11px] font-black flex items-center transition-all ${activeTab[i] === 'graph' ? 'bg-white text-primary shadow-lg shadow-black/5 ring-1 ring-black/5' : 'text-slate-400 hover:text-slate-600'}`}
                              onClick={() => setActiveTab(prev => ({ ...prev, [i]: 'graph' }))}
                            >
                              <Calculator className="h-3 w-3 inline mr-2 opacity-50" /> VISUALIZER
                            </button>
                          </div>
                        </div>
                        
                        <div className="bg-white rounded-[2.5rem] p-2 shadow-2xl shadow-slate-200 border border-slate-100 overflow-hidden">
                          {activeTab[i] === 'explanation' ? (
                            <div className="bg-slate-50/50 rounded-[2rem] p-12 text-center space-y-4">
                              <div className="bg-white w-16 h-16 rounded-full flex items-center justify-center mx-auto shadow-xl ring-1 ring-slate-100">
                                <LineChart className="h-8 w-8 text-primary" />
                              </div>
                              <h3 className="text-xl font-black text-slate-800 tracking-tight">Geometric Mapping</h3>
                              <p className="text-slate-500 max-w-xs mx-auto text-sm font-medium leading-relaxed">
                                Switch to the visualizer to explore the structural representation of the computed solution.
                              </p>
                            </div>
                          ) : (
                            <div className="animate-in zoom-in-95 duration-700">
                              <DesmosGraph equations={msg.plot_equation} />
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Compact Thinking Indicator */}
            {isLoading && messages[messages.length-1]?.bot === 'Thinking...' && (
              <ThinkingIndicator />
            )}
          </div>
        </div>

        {/* Input Bar */}
        <div className="p-10 bg-gradient-to-t from-white via-white/80 to-transparent backdrop-blur-md">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative group">
            <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 to-emerald-500/20 rounded-[2rem] blur opacity-0 group-focus-within:opacity-100 transition duration-500"></div>
            <div className="relative">
              <Input 
                placeholder="Initialize math query..." 
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                disabled={isLoading}
                className="h-16 pl-8 pr-20 rounded-[1.8rem] border-slate-200 bg-white shadow-2xl focus-visible:ring-primary/20 transition-all text-base font-medium placeholder:text-slate-400"
              />
              <Button 
                type="submit" 
                disabled={isLoading || !inputValue.trim()}
                className="absolute right-2 top-2 h-12 w-12 rounded-2xl p-0 shadow-xl active:scale-95 transition-transform"
              >
                {isLoading ? (
                  <div className="h-4 w-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </form>
          <div className="flex justify-center items-center mt-6 space-x-6">
             <div className="flex items-center text-[9px] font-black text-slate-400 uppercase tracking-widest">
               <span className="h-1 w-1 bg-primary rounded-full mr-2"></span> Math-Engine: G2.5-F
             </div>
             <div className="flex items-center text-[9px] font-black text-slate-400 uppercase tracking-widest">
               <span className="h-1 w-1 bg-emerald-500 rounded-full mr-2"></span> Logic-Core: Stabilized
             </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
