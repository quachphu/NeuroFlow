import { useState, useEffect, useRef } from 'react';
import { endFocus } from '../api';
import { X, Pause, Play } from 'lucide-react';

export default function FocusTimer({ duration = 15, onEnd }) {
  const totalSeconds = duration * 60;
  const [remaining, setRemaining] = useState(totalSeconds);
  const [paused, setPaused] = useState(false);
  const [rating, setRating] = useState(null);
  const [done, setDone] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (paused || done) return;
    intervalRef.current = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          clearInterval(intervalRef.current);
          setDone(true);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(intervalRef.current);
  }, [paused, done]);

  const progress = 1 - remaining / totalSeconds;
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const circumference = 2 * Math.PI * 45;
  const offset = circumference * (1 - progress);

  async function handleEnd(r) {
    setRating(r);
    try { await endFocus(r); } catch {}
    setTimeout(() => onEnd(), 800);
  }

  if (done && rating === null) {
    return (
      <div className="bg-sage/10 border-b border-sage/20 px-6 py-4 animate-fade-in">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-sage">Session complete!</p>
            <p className="text-xs text-text-muted">How did it go?</p>
          </div>
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map((r) => (
              <button
                key={r}
                onClick={() => handleEnd(r)}
                className="w-9 h-9 rounded-lg text-lg hover:bg-sage/20 transition-colors"
              >
                {r <= 2 ? '😔' : r === 3 ? '😐' : r === 4 ? '😊' : '🤩'}
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber/5 border-b border-amber/15 px-6 py-3 animate-fade-in">
      <div className="max-w-3xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          {/* Mini circular timer */}
          <div className="relative w-11 h-11">
            <svg className="w-11 h-11 -rotate-90" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="45" fill="none" stroke="#E8E6E1" strokeWidth="6" />
              <circle
                cx="50" cy="50" r="45" fill="none"
                stroke="#D4A76A"
                strokeWidth="6"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                className="transition-[stroke-dashoffset] duration-1000"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-[10px] font-semibold text-amber">
              {minutes}:{seconds.toString().padStart(2, '0')}
            </span>
          </div>
          <div>
            <p className="text-sm font-medium text-text">Focus session</p>
            <p className="text-xs text-text-muted">{duration} min · {Math.round(progress * 100)}% complete</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused(!paused)}
            className="p-2 rounded-lg hover:bg-amber/10 transition-colors text-amber"
          >
            {paused ? <Play size={16} /> : <Pause size={16} />}
          </button>
          <button
            onClick={() => { setDone(true); }}
            className="p-2 rounded-lg hover:bg-red-50 transition-colors text-text-muted hover:text-red-400"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
