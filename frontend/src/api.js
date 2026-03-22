const BASE = '/api';

export async function sendChat(message) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

export async function uploadAudio(file) {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
  return res.json();
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
  const res = await fetch(`${BASE}/profile`);
  return res.json();
}
