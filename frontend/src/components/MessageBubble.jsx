const AGENT_COLORS = {
  transcription: 'bg-lavender/20 text-lavender',
  canvas: 'bg-amber/20 text-amber',
  calendar: 'bg-blue/20 text-blue',
  focus: 'bg-sage/20 text-sage',
  profile: 'bg-cream-dark text-text-muted',
};

const AGENT_LABELS = {
  transcription: '📝 Transcription',
  canvas: '📚 Canvas',
  calendar: '📅 Calendar',
  focus: '🎯 Focus',
  profile: '👤 Profile',
};

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[85%] ${isUser ? 'order-1' : 'order-1'}`}>
        {/* Agent badges */}
        {!isUser && message.agents?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-1.5 ml-1">
            {message.agents.map((agent) => (
              <span
                key={agent}
                className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${AGENT_COLORS[agent] || 'bg-cream-dark text-text-muted'}`}
              >
                {AGENT_LABELS[agent] || agent}
              </span>
            ))}
          </div>
        )}

        {/* Bubble */}
        <div
          className={`
            px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap
            ${isUser
              ? 'bg-blue text-white rounded-2xl rounded-br-md'
              : 'bg-white border border-border rounded-2xl rounded-bl-md shadow-sm'
            }
          `}
        >
          {message.text}
        </div>
      </div>
    </div>
  );
}
