const BASE = '/api';

export async function sendChat(message) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

/**
 * Stream chat via NDJSON — calls onEvent({ type, ... }) for each event.
 * Returns a promise that resolves with the final "done" event payload.
 */
export async function streamChat(message, onEvent) {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop(); // keep incomplete line in buffer

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const event = JSON.parse(trimmed);
        onEvent(event);
        if (event.type === 'done') result = event;
      } catch {
        // skip malformed lines
      }
    }
  }

  // handle any remaining buffer
  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer.trim());
      onEvent(event);
      if (event.type === 'done') result = event;
    } catch {
      // skip
    }
  }

  return result;
}

export async function startFocus(durationMinutes = 0) {
  const res = await fetch(`${BASE}/focus/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ duration_minutes: durationMinutes }),
  });
  return res.json();
}

export async function endFocus(rating = 3) {
  const res = await fetch(`${BASE}/focus/end`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating }),
  });
  return res.json();
}

export async function getFocusStats() {
  const res = await fetch(`${BASE}/focus/stats`);
  return res.json();
}

export async function getProfile() {
  const res = await fetch(`${BASE}/advisor`);
  return res.json();
}
