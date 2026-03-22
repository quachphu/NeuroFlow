import { useState, useEffect } from 'react';
import { getProfile, getFocusStats } from '../api';
import { X } from 'lucide-react';

const QUICK_ACTIONS = [
  { label: 'Start focus session', msg: 'Start a focus session' },
  { label: "What's on my schedule?", msg: "What's on my schedule today?" },
  { label: 'Check my grades', msg: 'What are my grades?' },
  { label: "I'm overwhelmed", msg: "I can't do this anymore, I'm overwhelmed" },
];

export default function Sidebar({ onClose, onSend }) {
  const [profile, setProfile] = useState(null);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getProfile().then(setProfile).catch(() => {});
    getFocusStats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className="absolute right-0 top-0 bottom-0 w-80 bg-white border-l border-border shadow-lg animate-fade-in overflow-y-auto z-10">
      <div className="p-5">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-sm font-semibold text-text">Dashboard</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-cream transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Profile card */}
        {profile && (
          <div className="bg-cream rounded-xl p-4 mb-4">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Profile</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Type</span>
                <span className="font-medium">{profile.disability_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Reading level</span>
                <span className="font-medium">Grade {profile.reading_grade_level}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Session length</span>
                <span className="font-medium">{profile.preferred_session_length} min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Tone</span>
                <span className="font-medium capitalize">{profile.tone}</span>
              </div>
            </div>
          </div>
        )}

        {/* Focus stats */}
        {stats && (
          <div className="bg-sage/5 rounded-xl p-4 mb-4">
            <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Today's Focus</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Sessions</span>
                <span className="font-medium">{stats.total_sessions ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Total minutes</span>
                <span className="font-medium">{stats.total_minutes ?? 0}</span>
              </div>
              {stats.streak !== undefined && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Streak</span>
                  <span className="font-medium">{stats.streak} days</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Quick Actions</h3>
          <div className="space-y-2">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => { onSend(action.msg); onClose(); }}
                className="w-full text-left px-3 py-2.5 rounded-xl text-sm bg-cream hover:bg-cream-dark transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Agents status */}
        <div className="mt-6">
          <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Active Agents</h3>
          <div className="grid grid-cols-2 gap-2">
            {['📝 Transcription', '📅 Calendar', '🎯 Focus', '📚 Canvas', '👤 Profile', '🧠 Orchestrator'].map((a) => (
              <div key={a} className="flex items-center gap-1.5 text-xs text-text-muted">
                <span className="w-1.5 h-1.5 rounded-full bg-sage" />
                {a}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
