import { useState } from 'react';
import Markdown from 'react-markdown';
import { ChevronDown, ChevronRight, ArrowRight, ExternalLink, BookOpen, AlertTriangle } from 'lucide-react';
import ScheduleProposal from './ScheduleProposal';

const AGENT_COLORS = {
  advisor: 'bg-lavender/15 text-lavender',
  calendar: 'bg-blue/15 text-blue',
  focus: 'bg-sage/15 text-sage',
  orchestrator: 'bg-amber/15 text-amber',
};

const AGENT_LABELS = {
  advisor: 'Advisor',
  calendar: 'Calendar',
  focus: 'Focus',
  orchestrator: 'Orchestrator',
};

const AGENT_DOT_COLORS = {
  advisor: 'bg-lavender',
  calendar: 'bg-blue',
  focus: 'bg-sage',
  orchestrator: 'bg-amber',
};

function ChainViz({ chainLog }) {
  const [expanded, setExpanded] = useState(false);
  if (!chainLog?.length) return null;

  return (
    <div className="mb-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-[11px] font-medium text-text-muted hover:text-text transition-colors"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span>Agent chain · {chainLog.length} steps</span>
      </button>

      {expanded && (
        <div className="mt-2 p-3 bg-cream rounded-xl space-y-1.5">
          {chainLog.map((step, i) => {
            const isAgentToAgent = step.from !== 'orchestrator' && step.to !== 'orchestrator';
            return (
              <div
                key={i}
                className={`flex items-center gap-1.5 text-[11px] leading-relaxed ${
                  isAgentToAgent ? 'font-medium' : 'opacity-70'
                }`}
              >
                <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${AGENT_DOT_COLORS[step.from] || 'bg-text-muted'}`} />
                <span className={`px-1.5 py-0.5 rounded-md ${AGENT_COLORS[step.from] || ''}`}>
                  {AGENT_LABELS[step.from] || step.from}
                </span>
                <ArrowRight size={10} className="text-text-muted/40" />
                <span className={`px-1.5 py-0.5 rounded-md ${AGENT_COLORS[step.to] || ''}`}>
                  {AGENT_LABELS[step.to] || step.to}
                </span>
                <span className="text-text-muted ml-1 truncate">{step.action}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function SourceCards({ sources }) {
  const [expanded, setExpanded] = useState(false);
  if (!sources?.length) return null;

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1.5 text-[11px] font-semibold text-text-muted hover:text-text transition-colors uppercase tracking-wider"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <BookOpen size={10} />
        <span>{sources.length} research source{sources.length !== 1 ? 's' : ''}</span>
      </button>
      {expanded && (
        <div className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-3 bg-card rounded-xl border border-border hover:shadow-sm transition-all group"
            >
              <ExternalLink size={12} className="mt-0.5 flex-shrink-0 text-text-muted opacity-40 group-hover:opacity-100 transition-opacity" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-text leading-tight">{s.title}</p>
                {s.snippet && (
                  <p className="text-[11px] text-text-muted leading-snug mt-1 line-clamp-2">{s.snippet}</p>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function CanvasCards({ canvas }) {
  const [expanded, setExpanded] = useState(false);
  if (!canvas?.upcoming?.length) return null;

  const urgent = canvas.upcoming.filter((a) => a.days_left <= 3);
  const later = canvas.upcoming.filter((a) => a.days_left > 3);

  return (
    <div className="mt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-[11px] font-semibold text-text-muted hover:text-text transition-colors uppercase tracking-wider"
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <span>{canvas.upcoming.length} Canvas assignments</span>
        {urgent.length > 0 && (
          <span className="px-2 py-0.5 bg-red/10 text-red rounded-full text-[10px] font-bold normal-case tracking-normal">
            {urgent.length} due soon
          </span>
        )}
      </button>
      {expanded && (
        <div className="mt-2 space-y-2">
          {urgent.map((a, i) => (
            <div key={`u${i}`} className="p-3 bg-red/5 rounded-xl border border-red/15">
              <div className="flex items-start gap-2">
                <AlertTriangle size={12} className="flex-shrink-0 text-red mt-0.5" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-text">{a.title}</p>
                  <p className="text-[11px] text-red mt-0.5">{a.course_name} · Due in {a.days_left}d · {a.weight}</p>
                </div>
              </div>
            </div>
          ))}
          {later.map((a, i) => (
            <div key={`n${i}`} className="p-3 bg-card rounded-xl border border-border">
              <p className="text-xs font-semibold text-text">{a.title}</p>
              <p className="text-[11px] text-text-muted mt-0.5">{a.course_name} · Due in {a.days_left}d · {a.weight}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div className={`max-w-[85%]`}>
        {/* Agent badges */}
        {!isUser && message.agents?.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {message.agents.map((agent) => (
              <span
                key={agent}
                className={`text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                  AGENT_COLORS[agent] || 'bg-cream-dark text-text-muted'
                }`}
              >
                {AGENT_LABELS[agent] || agent}
              </span>
            ))}
          </div>
        )}

        {/* Chain visualization */}
        {!isUser && <ChainViz chainLog={message.chainLog} />}

        {/* Bubble */}
        <div
          className={`
            px-5 py-4 text-sm leading-relaxed
            ${
              isUser
                ? 'bg-primary text-white rounded-2xl rounded-br-sm'
                : 'bg-card border border-border rounded-2xl rounded-bl-sm shadow-sm prose-bubble'
            }
          `}
        >
          {isUser ? message.text : <Markdown>{message.text}</Markdown>}
        </div>

        {/* Schedule proposal */}
        {!isUser && message.proposedSlots?.length > 0 && (
          <ScheduleProposal slots={message.proposedSlots} />
        )}

        {/* Research sources */}
        {!isUser && <SourceCards sources={message.sources} />}

        {/* Canvas assignments */}
        {!isUser && <CanvasCards canvas={message.canvas} />}
      </div>
    </div>
  );
}
