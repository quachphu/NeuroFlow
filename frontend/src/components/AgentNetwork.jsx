import { useEffect, useRef } from 'react';

const AGENT_COLORS = {
  orchestrator: '#C4944A',
  advisor: '#9B8BC4',
  focus: '#6B9E67',
  calendar: '#4A7FB5',
};

const AGENT_LABELS = {
  orchestrator: 'Orchestrator',
  advisor: 'Advisor',
  focus: 'Focus',
  calendar: 'Calendar',
};

function AgentAvatar({ agentId, size = 24, active = false }) {
  const color = AGENT_COLORS[agentId] || '#8A8A8A';
  const label = AGENT_LABELS[agentId] || agentId || '?';
  const letter = label.charAt(0).toUpperCase();

  return (
    <span
      className={`agent-avatar${active ? ' agent-avatar--active' : ''}`}
      style={{
        width: size,
        height: size,
        minWidth: size,
        backgroundColor: color + '20',
        borderColor: color,
        color: color,
        fontSize: size * 0.45,
      }}
    >
      {letter}
    </span>
  );
}

function StepCard({ step, isActive, isLast, index }) {
  const { from, to, action, detail } = step;
  const isHandoff = from && to && from !== to;
  const primaryAgent = isHandoff ? from : (step.active || to || from || 'orchestrator');
  const primaryColor = AGENT_COLORS[primaryAgent] || '#8A8A8A';

  return (
    <div
      className={`agent-step agent-step-enter${isActive ? ' agent-step--active' : ''}${!isActive && !isLast ? ' agent-step--past' : ''}`}
      style={{ animationDelay: `${index * 0.06}s` }}
    >
      {/* Timeline connector */}
      <div className="agent-step-timeline">
        <AgentAvatar agentId={primaryAgent} size={22} active={isActive} />
        {!isLast && <div className="agent-step-line" style={{ backgroundColor: primaryColor + '30' }} />}
      </div>

      {/* Content */}
      <div className="agent-step-content">
        <div className="agent-step-header">
          <span className="agent-step-name" style={{ color: primaryColor }}>
            {AGENT_LABELS[primaryAgent] || primaryAgent}
          </span>
          {isHandoff && (
            <>
              <span className="agent-step-arrow">→</span>
              <span className="agent-step-name" style={{ color: AGENT_COLORS[to] || '#8A8A8A' }}>
                {AGENT_LABELS[to] || to}
              </span>
            </>
          )}
          {isActive && <span className="agent-step-pulse" style={{ backgroundColor: primaryColor }} />}
        </div>

        {action && (
          <div className="agent-step-action">
            {action}
          </div>
        )}

        {detail && (
          <div className="agent-step-detail">
            <span className="agent-step-detail-branch">╰</span> {detail}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AgentNetwork({ steps, activeAgent, currentAction }) {
  const feedRef = useRef(null);

  // Auto-scroll to bottom when new steps appear
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [steps, currentAction]);

  const hasSteps = steps.length > 0;
  const showThinking = currentAction && activeAgent;

  return (
    <div className="agent-feed-container animate-fade-in">
      <div className="agent-feed" ref={feedRef}>
        {steps.map((step, i) => {
          const isLast = i === steps.length - 1 && !showThinking;
          const isActive = isLast && !showThinking;

          return (
            <StepCard
              key={`${i}-${step.action}`}
              step={step}
              isActive={isActive}
              isLast={isLast}
              index={i}
            />
          );
        })}

        {/* Current thinking indicator */}
        {showThinking && (
          <div className="agent-step agent-step-enter agent-step--active">
            <div className="agent-step-timeline">
              <AgentAvatar agentId={activeAgent} size={22} active />
            </div>
            <div className="agent-step-content">
              <div className="agent-step-header">
                <span
                  className="agent-step-name"
                  style={{ color: AGENT_COLORS[activeAgent] || '#8A8A8A' }}
                >
                  {AGENT_LABELS[activeAgent] || activeAgent}
                </span>
                <span className="agent-step-pulse" style={{ backgroundColor: AGENT_COLORS[activeAgent] || '#8A8A8A' }} />
              </div>
              <div className="agent-step-action agent-step-thinking">
                <span className="agent-thinking-dot" style={{ backgroundColor: AGENT_COLORS[activeAgent] || '#8A8A8A' }} />
                {currentAction}
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!hasSteps && !showThinking && (
          <div className="agent-feed-empty">
            <span className="agent-thinking-dot" style={{ backgroundColor: '#C4944A' }} />
            <span>Starting up...</span>
          </div>
        )}
      </div>
    </div>
  );
}
