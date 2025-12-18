import { useState } from "react";
import { shortlistResumes } from "../api/client";

export default function JDForm({ onResults, setLoading }) {
  const [jd, setJd] = useState("");
  const [category, setCategory] = useState("Pre-Sales");
  const [level, setLevel] = useState("fresher");

  const EXPERIENCE_MAP = {
    fresher: { min: 0, max: 2 },
    mid: { min: 2, max: 5 },
    senior: { min: 5, max: 10 },
    leadership: { min: 10, max: 40 },
  };

  const handleSubmit = async () => {
    if (!jd.trim()) {
      alert("Please enter Job Description");
      return;
    }

    const { min, max } = EXPERIENCE_MAP[level];
    setLoading(true);

    try {
      const data = await shortlistResumes({
        jd,
        minExp: min,
        maxExp: max,
        category,
      });

      // Normalize response for download compatibility
      const normalized = data.map((c) => ({
        ...c,
        item_id: c.item_id ?? c.resume_id,
      }));

      if (typeof onResults === "function") {
        onResults(normalized);
      }
    } catch (err) {
      console.error("Shortlist error:", err);
      alert("Failed to shortlist candidates");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="card-title">📋 Job Description</h2>
        <span className="card-hint">Define role requirements</span>
      </div>

      <label>JD TEXT</label>
      <textarea
        placeholder="Paste job description..."
        value={jd}
        onChange={(e) => setJd(e.target.value)}
      />

      <div className="exp-category-row">
        <div className="exp-block">
          <label>EXPERIENCE LEVEL</label>
          <div className="preset-group">
            {[
              ["fresher", "Fresher (0–2 yrs)"],
              ["mid", "Mid (2–5 yrs)"],
              ["senior", "Senior (5–10 yrs)"],
              ["leadership", "Leadership (10+ yrs)"],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                className={`preset ${level === key ? "active" : ""}`}
                onClick={() => setLevel(key)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="category-block">
          <label>CATEGORY</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            <option>Sales</option>
            <option>Pre-Sales</option>
          </select>
        </div>
      </div>

      <button type="button" className="btn-primary" onClick={handleSubmit}>
        🔍 Shortlist Candidates
      </button>
    </div>
  );
}
