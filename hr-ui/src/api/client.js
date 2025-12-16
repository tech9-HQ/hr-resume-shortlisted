const API_BASE = "http://127.0.0.1:8000";

export async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);
  return res.json();
}

export async function shortlistResumes(payload) {
  const res = await fetch("http://127.0.0.1:8000/shortlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      jd_text: payload.jd,
      min_exp: payload.minExp,
      max_exp: payload.maxExp,
      category: payload.category,
    }),
  });

  return res.json();
}


export async function listResumes(limit = 20) {
  const res = await fetch(`${API_BASE}/resumes?limit=${limit}`);
  return res.json();
}
