import { useState } from 'react';
import { ArrowRight, Check } from 'lucide-react';

const DISABILITIES = [
  { id: 'ADHD', label: 'ADHD', desc: 'Short sessions, movement breaks, structured tasks', tone: 'encouraging' },
  { id: 'dyslexia', label: 'Dyslexia', desc: 'Audio-friendly, visual aids, simplified text', tone: 'patient' },
  { id: 'autism', label: 'Autism / ASD', desc: 'Predictable routines, precise language, sensory-aware', tone: 'precise' },
  { id: 'anxiety', label: 'Anxiety', desc: 'Gentle pacing, small wins, compassionate support', tone: 'calm' },
  { id: 'other', label: 'Other / Multiple', desc: "I'll describe my needs in chat", tone: 'encouraging' },
];

const SESSION_LENGTHS = [10, 15, 20, 25, 30, 45];

const FOCUS_TIMES = [
  { id: 'morning', label: 'Morning', desc: '8am – 12pm' },
  { id: 'afternoon', label: 'Afternoon', desc: '12pm – 5pm' },
  { id: 'evening', label: 'Evening', desc: '5pm – 10pm' },
  { id: 'varies', label: 'Varies', desc: "It depends" },
];

const CHALLENGES = [
  'Starting tasks', 'Staying focused', 'Time management',
  'Reading long text', 'Test anxiety', 'Organization',
  'Remembering deadlines', 'Sensory overload',
];

export default function ProfileSetup({ onComplete }) {
  const [step, setStep] = useState(0);
  const [disability, setDisability] = useState('');
  const [sessionLen, setSessionLen] = useState(15);
  const [focusTime, setFocusTime] = useState('');
  const [challenges, setChallenges] = useState([]);
  const [saving, setSaving] = useState(false);

  function toggleChallenge(c) {
    setChallenges((prev) =>
      prev.includes(c) ? prev.filter((x) => x !== c) : [...prev, c]
    );
  }

  async function handleFinish() {
    setSaving(true);
    const chosen = DISABILITIES.find((d) => d.id === disability);
    const profile = {
      disability_type: disability,
      preferred_session_length: sessionLen,
      tone: chosen?.tone || 'encouraging',
      best_focus_time: focusTime,
      challenges,
    };
    try {
      await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profile),
      });
    } catch { /* continue */ }
    setSaving(false);
    onComplete(profile);
  }

  const steps = [
    // Step 0: Disability
    <div key="disability">
      <h2 className="text-2xl font-semibold text-text mb-2">What should I know about how you learn?</h2>
      <p className="text-sm text-text-muted mb-6">This helps me adapt strategies, pacing, and tone to work best for you.</p>
      <div className="space-y-2.5">
        {DISABILITIES.map((d) => (
          <button
            key={d.id}
            onClick={() => setDisability(d.id)}
            className={`w-full text-left p-4 rounded-2xl border-2 transition-all ${
              disability === d.id
                ? 'border-primary bg-card shadow-sm'
                : 'border-transparent bg-card/60 hover:bg-card hover:shadow-sm'
            }`}
          >
            <p className="text-sm font-semibold text-text">{d.label}</p>
            <p className="text-xs text-text-muted mt-0.5">{d.desc}</p>
          </button>
        ))}
      </div>
    </div>,

    // Step 1: Session length
    <div key="session">
      <h2 className="text-2xl font-semibold text-text mb-2">How long can you focus comfortably?</h2>
      <p className="text-sm text-text-muted mb-6">We'll build sessions around this. You can always change it later.</p>
      <div className="flex flex-wrap gap-3">
        {SESSION_LENGTHS.map((len) => (
          <button
            key={len}
            onClick={() => setSessionLen(len)}
            className={`px-5 py-3 rounded-2xl text-sm font-semibold transition-all ${
              sessionLen === len
                ? 'bg-primary text-white shadow-sm'
                : 'bg-card text-text-muted hover:bg-card hover:shadow-sm'
            }`}
          >
            {len} min
          </button>
        ))}
      </div>
    </div>,

    // Step 2: Focus time
    <div key="focus-time">
      <h2 className="text-2xl font-semibold text-text mb-2">When do you focus best?</h2>
      <p className="text-sm text-text-muted mb-6">I'll suggest study sessions during your peak time.</p>
      <div className="grid grid-cols-2 gap-3">
        {FOCUS_TIMES.map((t) => (
          <button
            key={t.id}
            onClick={() => setFocusTime(t.id)}
            className={`text-left p-4 rounded-2xl border-2 transition-all ${
              focusTime === t.id
                ? 'border-primary bg-card shadow-sm'
                : 'border-transparent bg-card/60 hover:bg-card hover:shadow-sm'
            }`}
          >
            <p className="text-sm font-semibold text-text">{t.label}</p>
            <p className="text-xs text-text-muted mt-0.5">{t.desc}</p>
          </button>
        ))}
      </div>
    </div>,

    // Step 3: Challenges
    <div key="challenges">
      <h2 className="text-2xl font-semibold text-text mb-2">What's hardest for you?</h2>
      <p className="text-sm text-text-muted mb-6">Select all that apply — I'll tailor strategies accordingly.</p>
      <div className="flex flex-wrap gap-2.5">
        {CHALLENGES.map((c) => (
          <button
            key={c}
            onClick={() => toggleChallenge(c)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
              challenges.includes(c)
                ? 'bg-primary text-white'
                : 'bg-card text-text-muted hover:bg-card hover:text-text hover:shadow-sm'
            }`}
          >
            {challenges.includes(c) && <Check size={12} className="inline mr-1.5 -mt-0.5" />}
            {c}
          </button>
        ))}
      </div>
    </div>,
  ];

  const isLastStep = step === steps.length - 1;
  const canAdvance = step === 0 ? disability : step === 2 ? focusTime : true;

  return (
    <div className="w-full max-w-lg mx-auto px-6 py-12 animate-fade-in">
      {/* Progress dots */}
      <div className="flex items-center justify-center gap-2 mb-10">
        {steps.map((_, i) => (
          <div
            key={i}
            className={`rounded-full transition-all duration-300 ${
              i === step ? 'w-7 h-2 bg-primary' : i < step ? 'w-2 h-2 bg-primary/40' : 'w-2 h-2 bg-border'
            }`}
          />
        ))}
      </div>

      {/* Current step */}
      {steps[step]}

      {/* Navigation */}
      <div className="flex items-center justify-between mt-10">
        {step > 0 ? (
          <button
            onClick={() => setStep(step - 1)}
            className="text-sm text-text-muted hover:text-text transition-colors"
          >
            Back
          </button>
        ) : (
          <button
            onClick={() => onComplete(null)}
            className="text-sm text-text-muted hover:text-text transition-colors"
          >
            Skip setup
          </button>
        )}

        <button
          onClick={isLastStep ? handleFinish : () => setStep(step + 1)}
          disabled={!canAdvance || saving}
          className="flex items-center gap-2 px-6 py-3 bg-primary text-white text-sm font-semibold rounded-full hover:bg-primary/90 transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-sm"
        >
          {saving ? 'Saving...' : isLastStep ? "Let's go" : 'Continue'}
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
