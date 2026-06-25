import { useState, useRef } from "react";
import { startInterview } from "../api/client";

export default function NewInterview({ onStarted, onCancel }) {
  const [name, setName]       = useState("");
  const [position, setPosition] = useState("");
  const [jd, setJd]           = useState("");
  const [file, setFile]       = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  const fileRef = useRef();

  const handleSubmit = async () => {
    if (!name.trim())     { setError("Candidate name is required."); return; }
    if (!position.trim()) { setError("Position / role is required."); return; }
    if (!jd.trim())       { setError("Please paste the Job Description."); return; }
    if (!file)            { setError("Please upload the candidate's resume."); return; }

    setError("");
    setLoading(true);
    try {
      const session = await startInterview(name.trim(), position.trim(), jd, file);
      onStarted(session);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <h2 className="card-title">🎤 New Interview</h2>
          <span className="card-hint">Fill in the details — AI will generate tailored questions</span>
        </div>
        {onCancel && (
          <button className="btn-secondary" style={{ marginTop: 0 }} onClick={onCancel}>
            ← Back
          </button>
        )}
      </div>

      {/* Row: Name + Position */}
      <div className="form-two-col" style={{ marginBottom: 16 }}>
        <div>
          <label>CANDIDATE NAME</label>
          <input
            type="text"
            placeholder="e.g. Priya Sharma"
            value={name}
            onChange={(e) => { setName(e.target.value); setError(""); }}
          />
        </div>
        <div>
          <label>POSITION / ROLE</label>
          <input
            type="text"
            placeholder="e.g. Senior Backend Engineer"
            value={position}
            onChange={(e) => { setPosition(e.target.value); setError(""); }}
          />
        </div>
      </div>

      {/* JD */}
      <label>JOB DESCRIPTION</label>
      <textarea
        placeholder="Paste the full job description here..."
        value={jd}
        onChange={(e) => { setJd(e.target.value); setError(""); }}
        style={{ minHeight: 160, marginBottom: 16 }}
      />

      {/* Resume upload */}
      <label>RESUME (PDF / DOCX / TXT)</label>
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.docx,.doc,.txt"
        onChange={(e) => { setFile(e.target.files[0] || null); setError(""); }}
        style={{ marginBottom: 0 }}
      />
      {file && (
        <p style={{ fontSize: 13, color: "var(--muted)", marginTop: 6 }}>
          Selected: {file.name}
        </p>
      )}

      {error && (
        <p style={{ color: "#dc2626", fontSize: 13, marginTop: 12 }}>{error}</p>
      )}

      <button
        className="btn-primary"
        onClick={handleSubmit}
        disabled={loading}
        style={{ marginTop: 20, width: "100%", fontSize: 15 }}
      >
        {loading ? "Parsing resume & generating questions…" : "Generate Interview Questions →"}
      </button>
    </div>
  );
}
