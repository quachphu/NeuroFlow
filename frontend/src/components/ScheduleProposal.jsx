import { useState } from 'react';
import { Check, Clock, CalendarCheck } from 'lucide-react';

export default function ScheduleProposal({ slots, onConfirm }) {
  const [selected, setSelected] = useState(() => new Set(slots.map((_, i) => i)));
  const [confirming, setConfirming] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  if (!slots?.length) return null;

  if (confirmed) {
    return (
      <div className="mt-4 p-4 bg-sage/8 rounded-2xl border border-sage/15 animate-fade-in">
        <div className="flex items-center gap-2 text-sm font-semibold text-sage">
          <CalendarCheck size={16} />
          {selected.size} session{selected.size !== 1 ? 's' : ''} added to your calendar
        </div>
      </div>
    );
  }

  function toggle(i) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  async function handleConfirm() {
    if (selected.size === 0) return;
    setConfirming(true);
    const chosen = slots.filter((_, i) => selected.has(i));
    try {
      const res = await fetch('/api/schedule/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slots: chosen }),
      });
      const data = await res.json();
      if (data.count > 0) {
        setConfirmed(true);
        onConfirm?.(data);
      }
    } catch { /* silent */ } finally {
      setConfirming(false);
    }
  }

  return (
    <div className="mt-4 space-y-3 animate-fade-in">
      <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
        Proposed study slots
      </p>

      <div className="space-y-2">
        {slots.map((slot, i) => {
          const isSelected = selected.has(i);
          return (
            <button
              key={i}
              onClick={() => toggle(i)}
              className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
                isSelected
                  ? 'border-primary bg-card shadow-sm'
                  : 'border-transparent bg-card/50 opacity-50'
              }`}
            >
              <div className="flex items-center gap-3">
                <div className={`w-5 h-5 rounded-md border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                  isSelected ? 'bg-primary border-primary' : 'border-border'
                }`}>
                  {isSelected && <Check size={12} className="text-white" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-semibold text-text">{slot.day}</p>
                    <p className="text-xs text-text-muted">{slot.date}</p>
                  </div>
                  <p className="text-xs text-text-muted flex items-center gap-1 mt-0.5">
                    <Clock size={10} />
                    {slot.start} – {slot.end} · {slot.duration_min} min
                  </p>
                  {slot.reason && (
                    <p className="text-[11px] text-sage mt-1.5 leading-snug">{slot.reason}</p>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex gap-2">
        <button
          onClick={handleConfirm}
          disabled={selected.size === 0 || confirming}
          className="flex-1 py-3 px-5 bg-primary text-white text-sm font-semibold rounded-full hover:bg-primary/90 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-sm"
        >
          {confirming ? 'Scheduling...' : `Add ${selected.size} to Calendar`}
        </button>
        <button
          onClick={() => setSelected(new Set())}
          className="py-3 px-4 text-sm text-text-muted hover:text-text rounded-full hover:bg-cream transition-colors"
        >
          Skip
        </button>
      </div>
    </div>
  );
}
