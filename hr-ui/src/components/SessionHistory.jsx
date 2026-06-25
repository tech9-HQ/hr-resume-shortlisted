import { useState, useEffect, useMemo } from "react";
import { listSessions, deleteSession, updateCandidate } from "../api/client";

const CATEGORIES = ["Sales", "Pre-Sales", "Technical", "Admin", "Management", "Finance", "Others"];

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

function StatCard({ label, value, accent }) {
  return (
    <div style={{
      background: "white", border: "1px solid var(--border)", borderRadius: "var(--radius)",
      padding: "18px 22px", flex: 1, boxShadow: "var(--shadow-sm)",
      borderTop: `3px solid ${accent || "var(--primary)"}`,
    }}>
      <div style={{ fontSize: 30, fontWeight: 900, color: accent || "var(--text)", lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: 11, fontWeight: 800, color: "var(--muted)", marginTop: 6, letterSpacing: 0.5 }}>{label}</div>
    </div>
  );
}

export default function SessionHistory({ onNewInterview, onContinue, onViewReport }) {
  const [sessions, setSessions]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState("");
  const [search, setSearch]         = useState("");
  const [filterCat, setFilterCat]   = useState("All");
  const [filterStatus, setFilterStatus] = useState("All");

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  // ── Stats ─────────────────────────────────────────────────────────────────
  const completed = sessions.filter((s) => s.status === "interviewed");
  const pending   = sessions.filter((s) => s.status === "pending");
  const scores    = completed.map((s) => s.overall_score).filter((v) => v != null);
  const avgScore  = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : null;

  // ── Filtered list ─────────────────────────────────────────────────────────
  const filtered = useMemo(() => sessions.filter((s) => {
    const nameHit   = !search.trim() || (s.candidate_name || "").toLowerCase().includes(search.toLowerCase().trim());
    const catHit    = filterCat    === "All" || s.category === filterCat;
    const statusHit = filterStatus === "All" || s.status   === filterStatus;
    return nameHit && catHit && statusHit;
  }), [sessions, search, filterCat, filterStatus]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleDelete = async (sessionId) => {
    if (!window.confirm("Delete this interview session? This cannot be undone.")) return;
    try {
      await deleteSession(sessionId);
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
    } catch (e) {
      alert("Delete failed: " + e.message);
    }
  };

  const handleCategoryChange = async (s, category) => {
    setSessions((prev) => prev.map((x) => x.session_id === s.session_id ? { ...x, category } : x));
    try { await updateCandidate(s.candidate_id, { category }); }
    catch (e) { alert("Save failed: " + e.message); }
  };

  const handleExperienceBlur = async (s, raw) => {
    const val = parseFloat(raw);
    if (isNaN(val) || val < 0 || val > 60) return;
    setSessions((prev) => prev.map((x) => x.session_id === s.session_id ? { ...x, experience: val } : x));
    try { await updateCandidate(s.candidate_id, { experience_years: val }); }
    catch (e) { alert("Save failed: " + e.message); }
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div>

      {/* Stats cards */}
      <div style={{ display: "flex", gap: 14, marginBottom: 20, flexWrap: "wrap" }}>
        <StatCard label="TOTAL INTERVIEWS"  value={sessions.length}                   accent="#0ea5e9" />
        <StatCard label="COMPLETED"         value={completed.length}                  accent="#16a34a" />
        <StatCard label="PENDING"           value={pending.length}                    accent="#b45309" />
        <StatCard label="AVG SCORE"         value={avgScore != null ? `${avgScore}%` : "—"} accent="#7c3aed" />
      </div>

      {/* Search + filters + CTA */}
      <div className="card" style={{ marginBottom: 16, padding: "14px 18px" }}>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="Search by name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ flex: "1 1 180px", marginBottom: 0 }}
          />
          <select
            value={filterCat}
            onChange={(e) => setFilterCat(e.target.value)}
            style={{ width: 160, marginBottom: 0 }}
          >
            <option value="All">All Categories</option>
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            style={{ width: 140, marginBottom: 0 }}
          >
            <option value="All">All Status</option>
            <option value="interviewed">Completed</option>
            <option value="pending">Pending</option>
          </select>
          <button
            className="btn-primary"
            style={{ marginTop: 0, whiteSpace: "nowrap" }}
            onClick={onNewInterview}
          >
            + New Interview
          </button>
        </div>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: "center", color: "var(--muted)", padding: 32 }}>Loading…</div>
      )}
      {error && (
        <div className="card" style={{ color: "#dc2626" }}>Error: {error}</div>
      )}

      {!loading && sessions.length === 0 && (
        <div className="card empty-history">
          <div style={{ fontSize: 40, marginBottom: 12 }}>📋</div>
          <h3 style={{ fontWeight: 800, marginBottom: 6 }}>No interviews yet</h3>
          <p style={{ color: "var(--muted)", fontSize: 14 }}>
            Click <strong>+ New Interview</strong> to get started.
          </p>
        </div>
      )}

      {!loading && sessions.length > 0 && filtered.length === 0 && (
        <div className="card" style={{ textAlign: "center", padding: 32, color: "var(--muted)" }}>
          No sessions match your filters.
        </div>
      )}

      {filtered.length > 0 && (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table className="history-table">
            <thead>
              <tr>
                <th>Candidate</th>
                <th>Position</th>
                <th style={{ width: 160 }}>Category</th>
                <th style={{ width: 110 }}>Experience (yrs)</th>
                <th style={{ width: 110 }}>Date</th>
                <th style={{ width: 80 }}>Score</th>
                <th style={{ width: 130 }}></th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => {
                const scoreColor = s.overall_score >= 70 ? "#16a34a" : s.overall_score >= 45 ? "#ca8a04" : "#dc2626";
                return (
                  <tr key={s.session_id} className="history-row">

                    {/* Candidate */}
                    <td>
                      <div style={{ fontWeight: 700 }}>{s.candidate_name || "—"}</div>
                      {s.candidate_email && (
                        <div style={{ fontSize: 12, color: "var(--muted)" }}>{s.candidate_email}</div>
                      )}
                    </td>

                    {/* Position */}
                    <td style={{ fontWeight: 600, fontSize: 13 }}>{s.position_title}</td>

                    {/* Category — inline dropdown */}
                    <td>
                      <select
                        value={s.category || ""}
                        onChange={(e) => handleCategoryChange(s, e.target.value)}
                        style={{ width: "100%", fontSize: 12, padding: "5px 8px", borderRadius: 8, marginBottom: 0 }}
                      >
                        <option value="">— Select —</option>
                        {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </td>

                    {/* Experience — inline number input */}
                    <td>
                      <input
                        key={s.session_id + "_" + s.experience}
                        type="number"
                        min="0" max="60" step="0.5"
                        defaultValue={s.experience ?? ""}
                        onBlur={(e) => handleExperienceBlur(s, e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && e.target.blur()}
                        style={{ width: 72, fontSize: 13, padding: "5px 8px", borderRadius: 8, marginBottom: 0 }}
                        placeholder="yrs"
                      />
                    </td>

                    {/* Date */}
                    <td style={{ fontSize: 13, color: "var(--muted)" }}>{formatDate(s.created_at)}</td>

                    {/* Score */}
                    <td>
                      {s.overall_score != null
                        ? <span style={{ fontWeight: 900, fontSize: 16, color: scoreColor }}>{s.overall_score}%</span>
                        : <span style={{ color: "var(--muted)", fontSize: 13 }}>—</span>
                      }
                    </td>

                    {/* Action */}
                    <td style={{ textAlign: "right" }}>
                      {s.status === "interviewed" ? (
                        <button
                          className="btn-secondary"
                          style={{ marginTop: 0, padding: "6px 12px", fontSize: 12, whiteSpace: "nowrap" }}
                          onClick={() => onViewReport(s)}
                        >
                          View Report
                        </button>
                      ) : (
                        <button
                          className="btn-primary"
                          style={{ marginTop: 0, padding: "6px 12px", fontSize: 12, whiteSpace: "nowrap" }}
                          onClick={() => onContinue(s)}
                        >
                          Continue →
                        </button>
                      )}
                    </td>

                    {/* Delete */}
                    <td style={{ textAlign: "center" }}>
                      <button
                        onClick={() => handleDelete(s.session_id)}
                        title="Delete session"
                        style={{
                          background: "none", border: "none", cursor: "pointer",
                          color: "#dc2626", fontSize: 15, padding: "4px 6px",
                          borderRadius: 6, opacity: 0.45, lineHeight: 1,
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.opacity = 1)}
                        onMouseLeave={(e) => (e.currentTarget.style.opacity = 0.45)}
                      >
                        ✕
                      </button>
                    </td>

                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
