import { useState } from "react";
import { useSettings } from "../context/SettingsContext";

const PRESET_COLORS = [
  "#0ea5e9", "#7c3aed", "#6366f1", "#f59e0b",
  "#16a34a", "#dc2626", "#ec4899", "#0891b2",
  "#ea580c", "#65a30d",
];

function SectionTitle({ children, sub }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ fontSize: 14, fontWeight: 900, color: "var(--text)" }}>{children}</div>
      {sub && <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

export default function Settings() {
  const { settings, updateSettings } = useSettings();

  // ── Local copies for editing ──────────────────────────────────────────────
  const [stages, setStages]         = useState(() => settings.stages.map((s) => ({ ...s })));
  const [categories, setCategories] = useState(() => [...settings.categories]);
  const [newCat, setNewCat]         = useState("");
  const [saved, setSaved]           = useState(false);
  const [saving, setSaving]         = useState(false);

  const handleSave = async () => {
    setSaving(true);
    await updateSettings({ stages, categories });
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  // ── Stage handlers ────────────────────────────────────────────────────────
  const updateStageLabel = (idx, label) =>
    setStages((prev) => prev.map((s, i) => i === idx ? { ...s, label } : s));

  const updateStageColor = (idx, color) =>
    setStages((prev) => prev.map((s, i) => i === idx ? { ...s, color } : s));

  const moveStage = (idx, dir) => {
    const next = [...stages];
    const swap = idx + dir;
    if (swap < 0 || swap >= next.length) return;
    [next[idx], next[swap]] = [next[swap], next[idx]];
    setStages(next);
  };

  // ── Category handlers ─────────────────────────────────────────────────────
  const addCategory = () => {
    const cat = newCat.trim();
    if (!cat || categories.includes(cat)) return;
    setCategories((prev) => [...prev, cat]);
    setNewCat("");
  };

  const removeCategory = (cat) =>
    setCategories((prev) => prev.filter((c) => c !== cat));

  return (
    <div className="settings-page">

      {/* ── Pipeline Stages ───────────────────────────────────────────────── */}
      <div className="card settings-section">
        <SectionTitle sub="Rename stages or change their colours. The order here matches the hiring pipeline.">
          Pipeline Stages
        </SectionTitle>

        <div className="settings-stages-list">
          {stages.map((stage, idx) => (
            <div key={stage.value} className="settings-stage-row">

              {/* Reorder arrows */}
              <div className="settings-stage-arrows">
                <button
                  className="arrow-btn"
                  onClick={() => moveStage(idx, -1)}
                  disabled={idx === 0}
                  title="Move up"
                >▲</button>
                <button
                  className="arrow-btn"
                  onClick={() => moveStage(idx, 1)}
                  disabled={idx === stages.length - 1}
                  title="Move down"
                >▼</button>
              </div>

              {/* Color dot + picker */}
              <div className="settings-color-wrap">
                <div
                  className="settings-color-dot"
                  style={{ background: stage.color }}
                />
                <div className="settings-color-presets">
                  {PRESET_COLORS.map((c) => (
                    <button
                      key={c}
                      className={`color-preset${stage.color === c ? " selected" : ""}`}
                      style={{ background: c }}
                      onClick={() => updateStageColor(idx, c)}
                      title={c}
                    />
                  ))}
                </div>
              </div>

              {/* Label */}
              <input
                className="settings-stage-input"
                value={stage.label}
                onChange={(e) => updateStageLabel(idx, e.target.value)}
                placeholder="Stage name"
              />

              {/* Key (read-only) */}
              <span className="settings-stage-key">{stage.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Candidate Categories ──────────────────────────────────────────── */}
      <div className="card settings-section">
        <SectionTitle sub="Categories used when classifying candidates. Used in filters and reports.">
          Candidate Categories
        </SectionTitle>

        <div className="settings-cats">
          {categories.map((cat) => (
            <div key={cat} className="settings-cat-chip">
              <span>{cat}</span>
              <button
                className="settings-cat-remove"
                onClick={() => removeCategory(cat)}
                title="Remove"
              >×</button>
            </div>
          ))}
        </div>

        <div className="settings-cat-add">
          <input
            type="text"
            placeholder="New category name…"
            value={newCat}
            onChange={(e) => setNewCat(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCategory()}
            style={{ marginBottom: 0, flex: 1 }}
          />
          <button className="btn-primary" style={{ marginTop: 0 }} onClick={addCategory}>
            Add
          </button>
        </div>
      </div>

      {/* ── Save ─────────────────────────────────────────────────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
        <button
          className="btn-primary"
          style={{ marginTop: 0, minWidth: 140 }}
          onClick={handleSave}
          disabled={saving}
        >
          {saving ? "Saving…" : "Save Settings"}
        </button>
        {saved && (
          <span style={{ fontSize: 13, color: "#16a34a", fontWeight: 700 }}>
            ✓ Saved successfully
          </span>
        )}
      </div>

    </div>
  );
}
