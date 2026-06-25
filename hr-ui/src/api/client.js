// hr-ui/src/api/client.js

export const API_BASE = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE) {
  throw new Error("VITE_API_BASE_URL is not defined. Set it in hr-ui/.env.local");
}

// ---------- Single-candidate interview setup ----------

export async function startInterview(candidateName, position, jdText, resumeFile) {
  const form = new FormData();
  form.append("candidate_name", candidateName);
  form.append("position", position);
  form.append("jd_text", jdText);
  form.append("resume", resumeFile);

  const res = await fetch(`${API_BASE}/sessions/start`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Failed to start interview: ${await res.text()}`);
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${API_BASE}/sessions`);
  if (!res.ok) throw new Error("Failed to load session history.");
  return res.json();
}

export async function deleteSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session.");
  return res.json();
}

export async function updateCandidate(candidateId, fields) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(fields),
  });
  if (!res.ok) throw new Error("Failed to update candidate.");
  return res.json();
}

// ---------- Session (bulk upload — legacy) ----------

export async function uploadSession(jdText, files) {
  const form = new FormData();
  form.append("jd_text", jdText);
  for (const f of files) form.append("resumes", f);

  const res = await fetch(`${API_BASE}/sessions/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error(`Upload failed: ${await res.text()}`);
  return res.json();
}

export async function fetchSession(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}`);
  if (!res.ok) throw new Error("Failed to load session.");
  return res.json();
}

// ---------- Interview ----------

export async function getQuestions(candidateId, sessionId) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}/questions?session_id=${sessionId}`);
  if (!res.ok) throw new Error(`Failed to load questions: ${await res.text()}`);
  return res.json();
}

export async function evaluateAnswers(candidateId, sessionId, answers) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, answers }),
  });
  if (!res.ok) throw new Error(`Evaluation failed: ${await res.text()}`);
  return res.json();
}

export async function getReport(candidateId, sessionId) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}/report?session_id=${sessionId}`);
  if (!res.ok) throw new Error("Report not found.");
  return res.json();
}

export async function updateCandidateStage(candidateId, stage) {
  const res = await fetch(`${API_BASE}/candidates/${candidateId}/stage`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage }),
  });
  if (!res.ok) throw new Error("Failed to update stage.");
  return res.json();
}

export async function getDashboardStats() {
  const res = await fetch(`${API_BASE}/dashboard/stats`);
  if (!res.ok) throw new Error("Failed to load dashboard stats.");
  return res.json();
}

export async function getSettings() {
  const res = await fetch(`${API_BASE}/settings`);
  if (!res.ok) throw new Error("Failed to load settings.");
  return res.json();
}

export async function saveSettings(settings) {
  const res = await fetch(`${API_BASE}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Failed to save settings.");
  return res.json();
}
