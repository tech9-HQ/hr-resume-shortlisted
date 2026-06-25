
const TYPE_STYLE = {
  Introduction: { bg: "#fef3c7", color: "#b45309" },
  Background:   { bg: "#dbeafe", color: "#1d4ed8" },
  Behavioral:   { bg: "#f3e8ff", color: "#7c3aed" },
  Compensation: { bg: "#dcfce7", color: "#16a34a" },
  Logistics:    { bg: "#f1f5f9", color: "#475569" },
};

function StarDisplay({ stars }) {
  const n = Math.max(0, Math.min(5, stars || 0));
  return (
    <span style={{ color: "#f59e0b", fontSize: 14, letterSpacing: 1 }}>
      {"★".repeat(n)}
      <span style={{ color: "#d1d5db" }}>{"★".repeat(5 - n)}</span>
    </span>
  );
}

function ScoreBar({ score }) {
  const color = score >= 70 ? "#16a34a" : score >= 45 ? "#ca8a04" : "#dc2626";
  return (
    <div style={{ background: "#e5e7eb", borderRadius: 999, height: 12, overflow: "hidden", flex: 1 }}>
      <div style={{ width: `${score}%`, background: color, height: "100%", borderRadius: 999 }} />
    </div>
  );
}

function ScorePill({ score }) {
  const bg = score >= 7 ? "#dcfce7" : score >= 5 ? "#fef9c3" : "#fee2e2";
  const color = score >= 7 ? "#16a34a" : score >= 5 ? "#b45309" : "#dc2626";
  return (
    <span style={{ background: bg, color, fontWeight: 800, fontSize: 12, padding: "4px 10px", borderRadius: 8, whiteSpace: "nowrap" }}>
      {score}/10
    </span>
  );
}

export default function ReportCard({ result, candidate, session, onBack, onReInterview }) {
  const { scored_answers = [], overall_score = 0, summary = "", strengths = [], concerns = [] } = result;

  return (
    <div>
      {/* Action bar — hidden on print */}
      <div className="no-print" style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        <button className="btn-secondary" style={{ marginTop: 0 }} onClick={onBack}>
          ← Back to Candidates
        </button>
        <button className="btn-primary" style={{ marginTop: 0 }} onClick={() => window.print()}>
          Print / Save PDF
        </button>
        <button className="btn-secondary" style={{ marginTop: 0 }} onClick={onReInterview}>
          Re-interview
        </button>
      </div>

      {/* Report card */}
      <div className="report-card">

        {/* Logo + title row */}
        <div className="report-brand">
          <span style={{ fontWeight: 900, fontSize: 15, letterSpacing: -0.3 }}>tech9labs</span>
          <span style={{ color: "var(--muted)", fontSize: 13 }}>Pre Screening Assistant — Interview Report</span>
        </div>

        {/* Candidate header */}
        <div className="report-header">
          <div>
            <h1 className="report-name">{candidate.name}</h1>
            <p className="report-meta">
              {candidate.email}
              {candidate.experience ? ` · ${candidate.experience} yrs experience` : ""}
              {candidate.category ? ` · ${candidate.category}` : ""}
            </p>
            <p style={{ fontSize: 14, color: "var(--text-soft)", marginTop: 6 }}>
              Position: <strong>{session.position_title}</strong>
            </p>
          </div>
        </div>

        {/* Score bar */}
        <div className="report-score-row">
          <div style={{ textAlign: "center", minWidth: 80 }}>
            <div style={{ fontSize: 38, fontWeight: 900, lineHeight: 1, color: overall_score >= 70 ? "#16a34a" : overall_score >= 45 ? "#ca8a04" : "#dc2626" }}>
              {overall_score}
            </div>
            <div style={{ fontSize: 11, fontWeight: 800, color: "var(--muted)", letterSpacing: 0.4 }}>OUT OF 100</div>
          </div>
          <ScoreBar score={overall_score} />
        </div>

        {/* Summary */}
        <div className="report-section">
          <div className="section-label">AI ASSESSMENT SUMMARY</div>
          <p style={{ lineHeight: 1.75, color: "var(--text-soft)", fontSize: 14 }}>{summary}</p>
        </div>

        {/* Strengths + Concerns */}
        <div className="report-two-col">
          <div className="report-section">
            <div className="section-label" style={{ color: "#16a34a" }}>STRENGTHS</div>
            <ul className="report-list">
              {strengths.map((s, i) => (
                <li key={i} style={{ color: "#166534" }}>{s}</li>
              ))}
            </ul>
          </div>
          <div className="report-section">
            <div className="section-label" style={{ color: "#dc2626" }}>CONCERNS</div>
            <ul className="report-list">
              {concerns.map((c, i) => (
                <li key={i} style={{ color: "#991b1b" }}>{c}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Q&A table */}
        <div className="report-section">
          <div className="section-label">SCREENING NOTES & SCORES</div>
          <table className="qa-table">
            <thead>
              <tr>
                <th style={{ width: 28 }}>#</th>
                <th>Question</th>
                <th style={{ width: 110 }}>Type</th>
                <th style={{ width: 100 }}>HR Rating</th>
                <th style={{ width: 70 }}>Score</th>
                <th>Notes & Feedback</th>
              </tr>
            </thead>
            <tbody>
              {scored_answers.map((qa, i) => {
                const ts = TYPE_STYLE[qa.type] || { bg: "#f3f4f6", color: "var(--text)" };
                return (
                  <tr key={i}>
                    <td style={{ fontWeight: 800, color: "var(--muted)", fontSize: 12 }}>{i + 1}</td>
                    <td style={{ fontWeight: 700, fontSize: 13 }}>{qa.question}</td>
                    <td>
                      <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 8px", borderRadius: 999, background: ts.bg, color: ts.color }}>
                        {qa.type}
                      </span>
                    </td>
                    <td><StarDisplay stars={qa.stars} /></td>
                    <td><ScorePill score={qa.score ?? 0} /></td>
                    <td style={{ fontSize: 12, lineHeight: 1.6 }}>
                      {qa.notes && (
                        <p style={{ color: "var(--text-soft)", marginBottom: 4 }}>
                          <strong>Notes:</strong> {qa.notes}
                        </p>
                      )}
                      <p style={{ color: "var(--muted)" }}>{qa.feedback}</p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Footer */}
        <div className="report-footer">
          Generated by Tech9Labs Pre Screening Assistant ·{" "}
          {new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "long", year: "numeric" })}
          <span style={{ margin: "0 10px" }}>·</span>
          <em>For internal HR use only</em>
        </div>
      </div>
    </div>
  );
}
