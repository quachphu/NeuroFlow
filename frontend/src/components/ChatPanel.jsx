import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { streamChat, sendChatViaAgents } from '../api';
import MessageBubble from './MessageBubble';
import AgentNetwork from './AgentNetwork';
import { ArrowUp, Zap, Radio } from 'lucide-react';

const ChatPanel = forwardRef(function ChatPanel({ onFocusStart }, ref) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'agent',
      text: "Welcome to **NeuroFlow**. I adapt to how your brain works best.\n\nTry asking me to help you study, plan your day, or start a focus session.",
      agents: [],
      intent: '',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [useAgents, setUseAgents] = useState(false);

  const [streamSteps, setStreamSteps] = useState([]);
  const [activeAgent, setActiveAgent] = useState(null);
  const [currentAction, setCurrentAction] = useState(null);
  const [streamIntent, setStreamIntent] = useState(null);
  const [streamSources, setStreamSources] = useState([]);

  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useImperativeHandle(ref, () => ({
    sendMessage: (text) => handleSend(text),
  }));

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, loading]);

  async function handleSend(text) {
    const msg = text || input.trim();
    if (!msg) return;
    setInput('');

    const userMsg = { id: Date.now(), role: 'user', text: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setStreamSteps([]);
    setActiveAgent('orchestrator');
    setCurrentAction('Classifying intent...');
    setStreamIntent(null);
    setStreamSources([]);

    try {
      if (useAgents) {
        // Real Fetch.ai agents via Agentverse
        setCurrentAction('Sending to Orchestrator agent on Agentverse...');
        setStreamSteps([
          { from: 'orchestrator', to: 'advisor', action: 'Routing through real Fetch.ai agents via Agentverse...', active: 'orchestrator' },
        ]);
        const result = await sendChatViaAgents(msg);
        const agentMsg = {
          id: Date.now() + 1,
          role: 'agent',
          text: result.response,
          agents: result.agents_used || [],
          intent: result.intent || '',
          sources: result.sources || [],
          canvas: result.canvas || null,
          proposedSlots: result.proposed_slots || [],
          via: 'agentverse',
        };
        setMessages((prev) => [...prev, agentMsg]);
      } else {
        // Fast simulated path with streaming visualization
        const result = await streamChat(msg, (event) => {
          if (event.type === 'intent') {
            setStreamIntent(event.intent);
            setCurrentAction(`Intent: ${event.intent}`);
          } else if (event.type === 'step') {
            setStreamSteps((prev) => [...prev, event]);
            setActiveAgent(event.active || event.to);
            setCurrentAction(event.action);
          } else if (event.type === 'sources') {
            setStreamSources(event.sources || []);
          }
        });

        if (result) {
          const agentMsg = {
            id: Date.now() + 1,
            role: 'agent',
            text: result.response,
            agents: result.agents_used || [],
            intent: result.intent || '',
            chainLog: result.chain_log || [],
            sources: result.sources || [],
            canvas: result.canvas || null,
            proposedSlots: result.proposed_slots || [],
          };
          setMessages((prev) => [...prev, agentMsg]);

          if (result.focus_started) {
            onFocusStart?.(result.focus_duration || 15);
          }
        }
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'agent', text: 'Something went wrong. Try again?', agents: [], intent: 'error' },
      ]);
    } finally {
      setLoading(false);
      setStreamSteps([]);
      setActiveAgent(null);
      setCurrentAction(null);
      setStreamIntent(null);
      setStreamSources([]);
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full">
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-8 space-y-5">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Live agent network visualization while streaming */}
        {loading && (
          <div className="flex flex-col items-center gap-4 py-6 animate-fade-in">
            <AgentNetwork
              steps={streamSteps}
              activeAgent={activeAgent}
              currentAction={currentAction}
            />
            {streamIntent && (
              <div className="flex items-center gap-2 text-xs text-text-muted">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-sage animate-pulse-soft" />
                Processing <span className="font-semibold text-text">{streamIntent}</span> request
              </div>
            )}
            {streamSources.length > 0 && (
              <div className="flex flex-wrap gap-2 max-w-[360px] animate-fade-in">
                {streamSources.map((s, i) => (
                  <a
                    key={i}
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] font-medium px-2.5 py-1 bg-card text-text-muted rounded-full border border-border hover:text-text hover:shadow-sm transition-all truncate max-w-[170px]"
                    title={s.title}
                  >
                    {s.title}
                  </a>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="px-5 pb-5 pt-2">
        <div className="flex items-end gap-3 bg-card rounded-2xl border border-border px-4 py-3 shadow-sm">
          <button
            onClick={() => setUseAgents((v) => !v)}
            title={useAgents ? 'Using real Fetch.ai agents (slower)' : 'Using local simulation (fast)'}
            className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${
              useAgents
                ? 'bg-sage text-white shadow-sm'
                : 'bg-cream text-text-muted hover:bg-cream-dark'
            }`}
          >
            {useAgents ? <Radio size={14} /> : <Zap size={14} />}
          </button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={useAgents ? "Via Fetch.ai Agentverse (takes ~12s)..." : "Ask anything — study help, focus session, schedule..."}
            rows={1}
            className="flex-1 resize-none bg-transparent outline-none text-sm text-text placeholder-text-muted leading-relaxed max-h-32"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center hover:bg-primary/80 transition-colors disabled:opacity-20 disabled:cursor-not-allowed flex-shrink-0"
          >
            <ArrowUp size={16} />
          </button>
        </div>
      </div>
    </div>
  );
});

export default ChatPanel;
