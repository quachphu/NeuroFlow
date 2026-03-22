import { useState, useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import { sendChat, uploadAudio } from '../api';
import MessageBubble from './MessageBubble';
import AudioUpload from './AudioUpload';
import { Send, Mic, Paperclip } from 'lucide-react';

const ChatPanel = forwardRef(function ChatPanel({ onFocusStart }, ref) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'agent',
      text: "Hey there! I'm NeuroFlow, your study companion. I adapt to how your brain works best.\n\nTry telling me about a lecture you recorded, ask for help studying, or just say hi.",
      agents: [],
      intent: '',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useImperativeHandle(ref, () => ({
    sendMessage: (text) => handleSend(text),
  }));

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  async function handleSend(text) {
    const msg = text || input.trim();
    if (!msg) return;
    setInput('');

    const userMsg = { id: Date.now(), role: 'user', text: msg };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChat(msg);
      const agentMsg = {
        id: Date.now() + 1,
        role: 'agent',
        text: data.response,
        agents: data.agents_used || [],
        intent: data.intent || '',
      };
      setMessages((prev) => [...prev, agentMsg]);

      if (data.intent === 'focus' && data.response.toLowerCase().includes('start')) {
        onFocusStart?.(15);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'agent', text: 'Something went wrong. Try again?', agents: [], intent: 'error' },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleAudioUpload(file) {
    setShowUpload(false);
    const userMsg = { id: Date.now(), role: 'user', text: `🎙️ Uploaded: ${file.name}` };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const uploadResult = await uploadAudio(file);

      const wordCount = uploadResult.word_count || '?';
      const duration = uploadResult.duration_seconds || '?';
      const source = uploadResult.source || 'unknown';
      const preview = uploadResult.transcript
        ? uploadResult.transcript.substring(0, 500) + (uploadResult.transcript.length > 500 ? '...' : '')
        : uploadResult.transcript_preview || '';

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'agent',
          text: `Transcription complete (${source === 'whisper' ? 'Whisper API' : source})\n${wordCount} words · ${duration}s audio\n\n--- Raw transcript ---\n${preview}`,
          agents: ['transcription'],
          intent: 'transcribe',
        },
      ]);

      setLoading(true);
      const data = await sendChat(`I just recorded my lecture. Simplify the transcript for me.`);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: 'agent',
          text: data.response,
          agents: data.agents_used || [],
          intent: data.intent || '',
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { id: Date.now() + 1, role: 'agent', text: 'Had trouble processing that audio. Try again?', agents: [], intent: 'error' },
      ]);
    } finally {
      setLoading(false);
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
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {loading && (
          <div className="flex items-center gap-2 px-4 py-3 animate-fade-in">
            <div className="flex gap-1">
              <span className="w-2 h-2 rounded-full bg-sage animate-pulse-soft" style={{ animationDelay: '0ms' }} />
              <span className="w-2 h-2 rounded-full bg-sage animate-pulse-soft" style={{ animationDelay: '300ms' }} />
              <span className="w-2 h-2 rounded-full bg-sage animate-pulse-soft" style={{ animationDelay: '600ms' }} />
            </div>
            <span className="text-sm text-text-muted">Agents working...</span>
          </div>
        )}
      </div>

      {/* Upload overlay */}
      {showUpload && (
        <AudioUpload
          onUpload={handleAudioUpload}
          onClose={() => setShowUpload(false)}
        />
      )}

      {/* Input bar */}
      <div className="px-4 pb-4 pt-2">
        <div className="flex items-end gap-2 bg-white rounded-2xl border border-border shadow-sm px-4 py-3">
          <button
            onClick={() => setShowUpload(!showUpload)}
            className="p-1.5 rounded-lg hover:bg-cream transition-colors text-text-muted hover:text-text"
            title="Upload audio"
          >
            <Paperclip size={18} />
          </button>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tell me about your lecture, ask for help studying..."
            rows={1}
            className="flex-1 resize-none bg-transparent outline-none text-sm text-text placeholder-text-muted leading-relaxed max-h-32"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="p-1.5 rounded-lg bg-blue text-white hover:bg-blue/90 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            <Send size={18} />
          </button>
        </div>
        <p className="text-center text-xs text-text-muted mt-2 opacity-60">
          6 agents working together — adapted to your learning style
        </p>
      </div>
    </div>
  );
});

export default ChatPanel;
