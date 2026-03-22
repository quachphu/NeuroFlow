import { useState, useRef } from 'react';
import ChatPanel from './components/ChatPanel';
import FocusTimer from './components/FocusTimer';
import Sidebar from './components/Sidebar';
import ProfileSetup from './components/ProfileSetup';

export default function App() {
  const [setupDone, setSetupDone] = useState(false);
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

  function handleSetupComplete() {
    setSetupDone(true);
  }

  if (!setupDone) {
    return (
      <div className="h-full flex flex-col bg-cream">
        <header className="flex items-center justify-center px-6 py-5 border-b border-border bg-card">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-sage flex items-center justify-center">
              <span className="text-white text-sm font-bold">N</span>
            </div>
            <span className="text-base font-semibold text-text tracking-tight">NeuroFlow</span>
          </div>
        </header>
        <div className="flex-1 flex items-start justify-center overflow-y-auto">
          <ProfileSetup onComplete={handleSetupComplete} />
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-cream">
      {focusActive && (
        <FocusTimer duration={focusDuration} onEnd={handleFocusEnd} />
      )}

      <header className="flex items-center justify-between px-6 py-4 border-b border-border bg-card">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-sage flex items-center justify-center">
            <span className="text-white text-sm font-bold">N</span>
          </div>
          <span className="text-base font-semibold text-text tracking-tight">NeuroFlow</span>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="w-8 h-8 rounded-full bg-cream hover:bg-cream-dark transition-colors flex items-center justify-center"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
        </button>
      </header>

      <div className="flex-1 flex overflow-hidden relative">
        <ChatPanel ref={chatRef} onFocusStart={handleFocusStart} />
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
