import { useState, useEffect } from "react";
import { getQuestions, evaluateAnswers, updateCandidate } from "../api/client";

const CATEGORIES = ["Sales", "Pre-Sales", "Technical", "Admin", "Management", "Finance", "Others"];

// Fixed colors for the 3 mandatory HR types
const FIXED_TYPE_STYLE = {
  Introduction: { bg: "#fef3c7", color: "#b45309" },
  Compensation: { bg: "#dcfce7", color: "#16a34a" },
  Logistics:    { bg: "#f1f5f9", color: "#475569" },
};

// Color palette rotated for profile-specific dynamic types
const DYNAMIC_PALETTE = [
  { bg: "#dbeafe", color: "#1d4ed8" },   // blue
  { bg: "#f3e8ff", color: "#7c3aed" },   // purple
  { bg: "#ffedd5", color: "#c2410c" },   // orange
  { bg: "#fce7f3", color: "#be185d" },   // pink
  { bg: "#ecfdf5", color: "#059669" },   // emerald
  { bg: "#e0f2fe", color: "#0369a1" },   // sky
  { bg: "#fef9c3", color: "#854d0e" },   // yellow
  { bg: "#f0fdf4", color: "#166534" },   // light green
];

function getTypeStyle(type, dynamicTypeList) {
  if (FIXED_TYPE_STYLE[type]) return FIXED_TYPE_STYLE[type];
  const idx = dynamicTypeList.indexOf(type);
  return DYNAMIC_PALETTE[Math.max(0, idx) % DYNAMIC_PALETTE.length];
}

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
  const [category, setCategory]   = useState(candidate.category || "");
  const [experience, setExperience] = useState(candidate.experience ?? "");

  const saveField = async (field, value) => {
    try {
      await updateCandidate(candidate.candidate_id, { [field]: value });
    } catch {
      // silent — not critical
    }
  };

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

  // Build ordered list of dynamic types (non-mandatory) for stable color assignment
  const dynamicTypeList = [...new Set(
    questions.map((q) => q.type).filter((t) => !FIXED_TYPE_STYLE[t])
  )];

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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div style={{ flex: 1 }}>
            <h2 style={{ fontWeight: 900, fontSize: 18 }}>{candidate.name}</h2>
            <p style={{ color: "var(--muted)", fontSize: 13, marginTop: 4 }}>
              {candidate.email}
            </p>
            <p style={{ fontSize: 13, color: "var(--text-soft)", marginTop: 4 }}>
              Position: <strong>{session.position_title}</strong>
            </p>

            {/* Editable category + experience */}
            <div className="form-two-col" style={{ marginTop: 14, maxWidth: 480 }}>
              <div>
                <label style={{ marginBottom: 5 }}>CATEGORY</label>
                <select
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    saveField("category", e.target.value);
                  }}
                  style={{ marginBottom: 0 }}
                >
                  <option value="">— Select —</option>
                  {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label style={{ marginBottom: 5 }}>EXPERIENCE (YRS)</label>
                <input
                  type="number"
                  min="0" max="60" step="0.5"
                  value={experience}
                  onChange={(e) => setExperience(e.target.value)}
                  onBlur={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val) && val >= 0) saveField("experience_years", val);
                  }}
                  onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
                  placeholder="e.g. 5.5"
                  style={{ marginBottom: 0 }}
                />
              </div>
            </div>
          </div>

          <button className="btn-secondary" style={{ marginTop: 0, flexShrink: 0 }} onClick={onBack}>
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
        const ts = getTypeStyle(q.type, dynamicTypeList);
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
