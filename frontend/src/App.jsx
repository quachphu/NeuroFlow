import { useState, useRef } from 'react';
import ChatPanel from './components/ChatPanel';
import FocusTimer from './components/FocusTimer';
import Sidebar from './components/Sidebar';

export default function App() {
  const [focusActive, setFocusActive] = useState(false);
  const [focusDuration, setFocusDuration] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const chatRef = useRef(null);

  function handleFocusStart(duration) {
    setFocusDuration(duration);
    setFocusActive(true);
  }

  function handleFocusEnd() {
    setFocusActive(false);
    setFocusDuration(null);
  }

  function handleSendFromSidebar(text) {
    if (chatRef.current?.sendMessage) chatRef.current.sendMessage(text);
  }

  return (
    <div className="h-full flex flex-col bg-cream">
      {/* Focus timer bar */}
      {focusActive && (
        <FocusTimer
          duration={focusDuration}
          onEnd={handleFocusEnd}
        />
      )}

      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-white/60 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-sage/20 flex items-center justify-center">
            <span className="text-sage text-lg">🧠</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-text tracking-tight">NeuroFlow</h1>
            <p className="text-xs text-text-muted">Your study companion</p>
          </div>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="w-9 h-9 rounded-xl bg-cream hover:bg-cream-dark transition-colors flex items-center justify-center"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
        </button>
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden relative">
        <ChatPanel
          ref={chatRef}
          onFocusStart={handleFocusStart}
        />
        {sidebarOpen && (
          <Sidebar
            onClose={() => setSidebarOpen(false)}
            onSend={handleSendFromSidebar}
          />
        )}
      </div>
    </div>
  );
}
