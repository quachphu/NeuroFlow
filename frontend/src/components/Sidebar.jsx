import { useState, useEffect } from 'react';
import { getProfile, getFocusStats } from '../api';
import { X } from 'lucide-react';

const QUICK_ACTIONS = [
  { label: 'Help me study for my midterm', msg: 'Help me study for my midterm this week' },
  { label: 'Start focus session', msg: 'Start a focus session' },
  { label: "What's on my schedule?", msg: "What's on my schedule today?" },
  { label: 'Plan my day', msg: 'Plan my day based on my schedule and needs' },
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
    <div className="absolute right-0 top-0 bottom-0 w-80 bg-card border-l border-border shadow-lg animate-fade-in overflow-y-auto z-10">
      <div className="p-6">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-xs font-semibold text-text-muted uppercase tracking-wider">Dashboard</h2>
          <button onClick={onClose} className="w-7 h-7 rounded-full hover:bg-cream flex items-center justify-center transition-colors">
            <X size={14} />
          </button>
        </div>

        {/* Advisor card */}
        {profile && (
          <div className="bg-card rounded-2xl p-5 mb-4 border border-border">
            <h3 className="text-[10px] font-semibold text-lavender uppercase tracking-wider mb-4">Advisor Profile</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Disability</span>
                <span className="font-semibold">{profile.disability_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Session length</span>
                <span className="font-semibold">{profile.preferred_session_length} min</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Tone</span>
                <span className="font-semibold capitalize">{profile.tone}</span>
              </div>
              {profile.best_focus_time && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Peak focus</span>
                  <span className="font-semibold capitalize">{profile.best_focus_time}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Focus stats */}
        {stats && (
          <div className="bg-card rounded-2xl p-5 mb-4 border border-border">
            <h3 className="text-[10px] font-semibold text-sage uppercase tracking-wider mb-4">Today's Focus</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Sessions</span>
                <span className="font-semibold">{stats.sessions_today ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Total minutes</span>
                <span className="font-semibold">{stats.total_focus_min ?? 0}</span>
              </div>
            </div>
          </div>
        )}

        {/* Quick actions */}
        <div>
          <h3 className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-3">Quick Actions</h3>
          <div className="space-y-2">
            {QUICK_ACTIONS.map((action) => (
              <button
                key={action.label}
                onClick={() => { onSend(action.msg); onClose(); }}
                className="w-full text-left px-4 py-3 rounded-xl text-sm text-text bg-cream hover:bg-cream-dark transition-colors"
              >
                {action.label}
              </button>
            ))}
          </div>
        </div>

        {/* Agents status */}
        <div className="mt-8">
          <h3 className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-3">Active Agents</h3>
          <div className="grid grid-cols-2 gap-2.5">
            {[
              { name: 'Advisor', color: 'bg-lavender' },
              { name: 'Focus', color: 'bg-sage' },
              { name: 'Calendar', color: 'bg-blue' },
              { name: 'Orchestrator', color: 'bg-amber' },
            ].map((a) => (
              <div key={a.name} className="flex items-center gap-2 text-xs text-text-muted">
                <span className={`w-2 h-2 rounded-full ${a.color}`} />
                {a.name}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
