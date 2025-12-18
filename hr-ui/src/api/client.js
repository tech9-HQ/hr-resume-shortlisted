// hr-ui/src/api/client.js

// ✅ API base must come ONLY from env (no localhost fallback)
export const API_BASE = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE) {
  throw new Error(
    "❌ VITE_API_BASE_URL is not defined. Check Azure Static Web App environment variables."
  );
}

// ------------------ API FUNCTIONS ------------------

export async function getStats() {
  const res = await fetch(`${API_BASE}/stats`);

  if (!res.ok) {
    throw new Error("Failed to fetch stats");
  }

  return res.json();
}

export async function shortlistResumes(payload) {
  const res = await fetch(`${API_BASE}/shortlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jd_text: payload.jd,
      min_exp: payload.minExp,
      max_exp: payload.maxExp,
      category: payload.category,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Shortlist failed: ${text}`);
  }

  return res.json();
}

export async function listResumes(limit = 20) {
  const res = await fetch(`${API_BASE}/resumes?limit=${limit}`);

  if (!res.ok) {
    throw new Error("Failed to list resumes");
  }

  return res.json();
}
