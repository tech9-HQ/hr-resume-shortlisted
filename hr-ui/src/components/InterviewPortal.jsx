import { useState, useEffect } from "react";
import { getQuestions, evaluateAnswers } from "../api/client";

const TYPE_STYLE = {
  Introduction: { bg: "#fef3c7", color: "#b45309" },
  Background:   { bg: "#dbeafe", color: "#1d4ed8" },
  Behavioral:   { bg: "#f3e8ff", color: "#7c3aed" },
  Compensation: { bg: "#dcfce7", color: "#16a34a" },
  Logistics:    { bg: "#f1f5f9", color: "#475569" },
};

function StarRating({ value, onChange }) {
  const [hovered, setHovered] = useState(0);
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          onClick={() => onChange(star === value ? 0 : star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          style={{
            background: "none", border: "none", cursor: "pointer",
            fontSize: 26, lineHeight: 1, padding: "2px 3px",
            color: star <= (hovered || value) ? "#f59e0b" : "#d1d5db",
            transition: "color 0.1s",
          }}
          title={["", "Poor", "Below average", "Average", "Good", "Excellent"][star]}
        >
          ★
        </button>
      ))}
      {value > 0 && (
        <span style={{ fontSize: 12, color: "var(--muted)", alignSelf: "center", marginLeft: 4 }}>
          {["", "Poor", "Below average", "Average", "Good", "Excellent"][value]}
        </span>
      )}
    </div>
  );
}

export default function InterviewPortal({ candidate, session, onComplete, onBack }) {
  const [questions, setQuestions] = useState([]);
  const [responses, setResponses] = useState({});   // {0: {notes:"", stars:0}, ...}
  const [loading, setLoading]     = useState(true);
  const [scoring, setScoring]     = useState(false);
  const [error, setError]         = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getQuestions(candidate.candidate_id, session.session_id)
      .then((data) => {
        setQuestions(data.questions || []);
        const init = {};
        (data.questions || []).forEach((_, i) => { init[i] = { notes: "", stars: 0 }; });
        setResponses(init);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [candidate.candidate_id, session.session_id]);

  const setField = (i, field, val) =>
    setResponses((prev) => ({ ...prev, [i]: { ...prev[i], [field]: val } }));

  const handleSubmit = async () => {
    const unrated = questions.filter((_, i) => !responses[i]?.stars).length;
    if (unrated > 0 && !window.confirm(`${unrated} question(s) have no star rating. Submit anyway?`)) return;

    setScoring(true);
    setError("");
    try {
      const qa = questions.map((q, i) => ({
        ...q,
        notes: responses[i]?.notes?.trim() || "",
        stars: responses[i]?.stars || 0,
      }));
      const result = await evaluateAnswers(candidate.candidate_id, session.session_id, qa);
      onComplete(result);
    } catch (e) {
      setError(e.message);
    } finally {
      setScoring(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ textAlign: "center", padding: 48 }}>
        <p style={{ fontWeight: 700, marginBottom: 8 }}>Generating interview questions…</p>
        <p style={{ color: "var(--muted)", fontSize: 13 }}>
          AI is personalising questions for {candidate.name} based on their resume.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* Candidate header */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h2 style={{ fontWeight: 900, fontSize: 18 }}>
              {candidate.name}
            </h2>
            <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
              {candidate.email}{candidate.experience ? ` · ${candidate.experience} yrs` : ""}{candidate.category ? ` · ${candidate.category}` : ""}
            </p>
            <p style={{ fontSize: 13, color: "var(--text-soft)", marginTop: 4 }}>
              Position: <strong>{session.position_title}</strong>
            </p>
          </div>
          <button className="btn-secondary" style={{ marginTop: 0 }} onClick={onBack}>
            ← Back
          </button>
        </div>
      </div>

      {/* Instruction banner */}
      <div style={{ background: "#eff6ff", border: "1px solid #bfdbfe", borderRadius: 10, padding: "12px 16px", marginBottom: 16, fontSize: 13, color: "#1e40af" }}>
        <strong>How to use:</strong> Ask each question during the phone call. Jot quick notes on what the candidate said, then rate their response with stars. Submit when done.
      </div>

      {/* Questions */}
      {questions.map((q, i) => {
        const ts = TYPE_STYLE[q.type] || { bg: "#f3f4f6", color: "var(--text)" };
        const resp = responses[i] || { notes: "", stars: 0 };
        return (
          <div key={i} className="card question-card">
            <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
              <div className="q-number">{i + 1}</div>
              <div style={{ flex: 1 }}>
                {/* Type + focus area badges */}
                <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, background: ts.bg, color: ts.color }}>
                    {q.type}
                  </span>
                  <span style={{ fontSize: 11, color: "var(--muted)", background: "#f3f4f6", padding: "3px 10px", borderRadius: 999 }}>
                    {q.focus_area}
                  </span>
                </div>

                {/* Question text */}
                <p style={{ fontWeight: 700, lineHeight: 1.6, marginBottom: 14, fontSize: 15 }}>{q.question}</p>

                {/* Star rating */}
                <div style={{ marginBottom: 10 }}>
                  <label style={{ marginBottom: 6 }}>RATING</label>
                  <StarRating value={resp.stars} onChange={(v) => setField(i, "stars", v)} />
                </div>

                {/* Notes */}
                <div>
                  <label style={{ marginBottom: 6 }}>NOTES FROM THE CALL</label>
                  <textarea
                    placeholder="Jot what the candidate said — key points, CTC figures, notice period, anything relevant..."
                    value={resp.notes}
                    onChange={(e) => setField(i, "notes", e.target.value)}
                    style={{ minHeight: 72 }}
                  />
                </div>
              </div>
            </div>
          </div>
        );
      })}

      {error && <p style={{ color: "#dc2626", marginBottom: 12 }}>{error}</p>}

      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={scoring}
        style={{ width: "100%", fontSize: 16 }}
      >
        {scoring ? "AI is generating the report… please wait" : "Submit & Generate Report"}
      </button>
    </div>
  );
}
