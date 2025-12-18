import { API_BASE } from "../api/client";

export default function ShortlistResults({ results, loading }) {
  const top3 = [...results]
    .sort((a, b) => b.score - a.score)
    .slice(0, 3);

  const handleDownload = (resumeId) => {
    if (!resumeId) {
      alert("Resume file not linked for this candidate");
      return;
    }

    window.open(`${API_BASE}/resumes/${resumeId}/download`, "_blank");
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">🏆 Top Matching Candidates</h2>
        <span className="card-hint">Best AI-fit profiles</span>
      </div>

      {loading && (
        <div className="empty-state">Analyzing resumes…</div>
      )}

      {!loading && top3.length === 0 && (
        <div className="empty-state">
          Results will appear here once the JD is analyzed
        </div>
      )}

      {!loading && top3.length > 0 && (
        <div className="results-grid">
          {top3.map((c) => (
            <div className="candidate-card" key={c.resume_id}>
              <div className="candidate-header">
                <h3>{c.name}</h3>
                <span className="fit-badge">{c.score}% Fit</span>
              </div>

              <p className="muted">{c.email}</p>

              <div className="meta">
                <span>
                  <b>{c.experience}</b> yrs experience
                </span>
              </div>

              <div className="fit">{c.fit}</div>

              <button
                className="btn-secondary"
                onClick={() => handleDownload(c.resume_id)}
              >
                ⬇ Download Resume
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
