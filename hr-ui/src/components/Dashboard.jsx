import { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from "recharts";
import { getDashboardStats } from "../api/client";
import { useSettings } from "../context/SettingsContext";

const CAT_COLORS = ["#0ea5e9", "#7c3aed", "#16a34a", "#f59e0b", "#ef4444", "#6366f1", "#ec4899"];

function MetricCard({ label, value, accent, sub }) {
  return (
    <div className="dash-metric-card" style={{ borderTop: `3px solid ${accent}` }}>
      <div className="dash-metric-value" style={{ color: accent }}>{value}</div>
      <div className="dash-metric-label">{label}</div>
      {sub && <div className="dash-metric-sub">{sub}</div>}
    </div>
  );
}

function SectionTitle({ children }) {
  return (
    <div className="dash-section-title">{children}</div>
  );
}

// Pipeline funnel — ordered stage bars
function PipelineFunnel({ byStage, stages }) {
  const stageMap = Object.fromEntries(byStage.map((s) => [s.stage, s.count]));
  const pipelineStages = stages.filter((s) => s.value !== "rejected");
  const data = pipelineStages.map((s) => ({
    name: s.label,
    count: stageMap[s.value] || 0,
    fill: s.color,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ left: 10, right: 30, top: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e5e7eb" />
        <XAxis type="number" tick={{ fontSize: 11, fill: "#6b7280" }} allowDecimals={false} />
        <YAxis type="category" dataKey="name" tick={{ fontSize: 11, fill: "#374151" }} width={120} />
        <Tooltip
          formatter={(v) => [v, "Candidates"]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Bar dataKey="count" radius={[0, 6, 6, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Score distribution bar chart
function ScoreDist({ data }) {
  const colored = data.map((d, i) => ({
    ...d,
    fill: ["#ef4444", "#f59e0b", "#0ea5e9", "#16a34a"][i],
  }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={colored} margin={{ left: -10, right: 10, top: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
        <XAxis dataKey="range" tick={{ fontSize: 11, fill: "#6b7280" }} />
        <YAxis tick={{ fontSize: 11, fill: "#6b7280" }} allowDecimals={false} />
        <Tooltip
          formatter={(v) => [v, "Candidates"]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
        <Bar dataKey="count" radius={[6, 6, 0, 0]}>
          {colored.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// Category pie chart
function CategoryPie({ data }) {
  if (!data.length) return <div className="dash-empty">No data yet</div>;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie
          data={data}
          dataKey="count"
          nameKey="category"
          cx="50%"
          cy="50%"
          outerRadius={80}
          label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
          labelLine={false}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CAT_COLORS[i % CAT_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(v, name) => [v, name]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

function RecentRow({ item }) {
  const scoreColor = item.score >= 70 ? "#16a34a" : item.score >= 45 ? "#ca8a04" : "#dc2626";
  const date = item.completed_at
    ? new Date(item.completed_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short" })
    : "—";
  return (
    <div className="dash-recent-row">
      <div>
        <div className="dash-recent-name">{item.name}</div>
        <div className="dash-recent-pos">{item.position}</div>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ fontSize: 11, color: "#6b7280" }}>{date}</span>
        {item.score != null && (
          <span style={{ fontWeight: 900, fontSize: 15, color: scoreColor }}>{item.score}%</span>
        )}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { settings } = useSettings();
  const [stats, setStats]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState("");

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="dash-loading">Loading dashboard…</div>;
  if (error)   return <div className="dash-error">Error: {error}</div>;
  if (!stats)  return null;

  return (
    <div className="dashboard">

      {/* Metric cards row */}
      <div className="dash-metrics">
        <MetricCard label="TOTAL CANDIDATES"  value={stats.total}                                accent="#0ea5e9" />
        <MetricCard label="COMPLETED"          value={stats.completed}                            accent="#16a34a" />
        <MetricCard label="PENDING"            value={stats.pending}                              accent="#b45309" />
        <MetricCard label="AVG SCORE"          value={stats.avg_score ? `${stats.avg_score}%` : "—"} accent="#7c3aed" />
        <MetricCard label="PASS RATE"          value={stats.pass_rate ? `${stats.pass_rate}%` : "—"} accent="#0ea5e9" sub="Score ≥ 70%" />
      </div>

      {/* Charts row 1: pipeline + score dist */}
      <div className="dash-row-2">
        <div className="card dash-chart-card">
          <SectionTitle>Hiring Pipeline</SectionTitle>
          <PipelineFunnel byStage={stats.by_stage} stages={settings.stages} />
        </div>
        <div className="card dash-chart-card">
          <SectionTitle>Score Distribution</SectionTitle>
          <ScoreDist data={stats.score_distribution} />
        </div>
      </div>

      {/* Charts row 2: category pie + recent */}
      <div className="dash-row-2">
        <div className="card dash-chart-card">
          <SectionTitle>By Category</SectionTitle>
          <CategoryPie data={stats.by_category} />
        </div>
        <div className="card dash-chart-card">
          <SectionTitle>Recent Interviews</SectionTitle>
          {stats.recent_interviews.length === 0 ? (
            <div className="dash-empty">No completed interviews yet</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
              {stats.recent_interviews.map((item, i) => (
                <RecentRow key={i} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
