import { useSettings } from "../context/SettingsContext";

function Section({ title, children }) {
  return (
    <div className="help-section">
      <h2 className="help-section-title">{title}</h2>
      {children}
    </div>
  );
}

function Step({ n, title, children }) {
  return (
    <div className="help-step">
      <div className="help-step-num">{n}</div>
      <div>
        <div className="help-step-title">{title}</div>
        <div className="help-step-body">{children}</div>
      </div>
    </div>
  );
}

function QA({ q, children }) {
  return (
    <div className="help-qa">
      <div className="help-q">{q}</div>
      <div className="help-a">{children}</div>
    </div>
  );
}

export default function Help() {
  const { settings } = useSettings();
  const pipelineStages = settings.stages.filter((s) => s.value !== "rejected");

  return (
    <div className="help-page">

      <div className="help-hero">
        <h1 className="help-title">Quick Reference Guide</h1>
        <p className="help-sub">Everything you need to use the Pre Screening Assistant effectively.</p>
      </div>

      {/* ── Getting Started ───────────────────────────────────────────────── */}
      <Section title="Getting Started">
        <Step n="1" title="Start a New Interview">
          Click <strong>Interviews</strong> in the sidebar, then <strong>+ New Interview</strong>.
          Enter the candidate name, position title, job description, and upload their resume (PDF or DOCX).
        </Step>
        <Step n="2" title="AI Question Generation">
          The system reads the resume and job description, then generates tailored interview questions
          across 5 types: Introduction, Background, Technical, Behavioral, and Logistics.
        </Step>
        <Step n="3" title="Conduct the Interview">
          For each question, rate the candidate's answer (1–5 stars) and optionally add notes.
          When done, click <strong>Submit Answers</strong>.
        </Step>
        <Step n="4" title="Review the Report">
          The AI scores all answers and generates an overall score (0–100), a recommendation
          (Hire / Maybe / No), a summary, strengths, and concerns. You can print or save the report.
        </Step>
        <Step n="5" title="Track Pipeline Progress">
          In the Interviews table, use the <strong>Stage</strong> dropdown on each row to move
          the candidate through the hiring pipeline. Changes save instantly.
        </Step>
      </Section>

      {/* ── Scoring Guide ─────────────────────────────────────────────────── */}
      <Section title="Understanding Scores">
        <div className="help-score-grid">
          {[
            { range: "71 – 100", label: "Strong Hire",  color: "#16a34a", desc: "Candidate meets or exceeds all requirements. Recommend moving to next round." },
            { range: "45 – 70",  label: "Maybe",        color: "#ca8a04", desc: "Mixed signals. Review concerns carefully before deciding." },
            { range: "0 – 44",   label: "No Hire",      color: "#dc2626", desc: "Significant gaps in skills or experience. Consider rejection." },
          ].map((s) => (
            <div key={s.range} className="help-score-card" style={{ borderLeft: `4px solid ${s.color}` }}>
              <div style={{ fontSize: 20, fontWeight: 900, color: s.color }}>{s.range}</div>
              <div style={{ fontWeight: 800, marginTop: 4 }}>{s.label}</div>
              <div style={{ fontSize: 12, color: "var(--muted)", marginTop: 6, lineHeight: 1.5 }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Pipeline Stages ───────────────────────────────────────────────── */}
      <Section title="Hiring Pipeline Stages">
        <p style={{ fontSize: 13, color: "var(--muted)", marginBottom: 16, lineHeight: 1.6 }}>
          Each candidate moves through your configured pipeline stages. You can rename stages
          in <strong>Settings</strong>. Mark a candidate as <strong style={{ color: "#dc2626" }}>Rejected</strong> at
          any stage to flag them without deleting their record.
        </p>
        <div className="help-stages">
          {pipelineStages.map((stage, i) => (
            <div key={stage.value} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div className="help-stage-badge" style={{ background: stage.color + "18", color: stage.color, border: `1px solid ${stage.color}40` }}>
                {stage.label}
              </div>
              {i < pipelineStages.length - 1 && (
                <span style={{ color: "var(--muted)", fontSize: 16 }}>→</span>
              )}
            </div>
          ))}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <span style={{ fontSize: 12, color: "var(--muted)" }}>or at any point:</span>
            <div className="help-stage-badge" style={{ background: "#dc262618", color: "#dc2626", border: "1px solid #dc262640" }}>
              Rejected
            </div>
          </div>
        </div>
      </Section>

      {/* ── Tips ──────────────────────────────────────────────────────────── */}
      <Section title="Tips & Best Practices">
        <ul className="help-tips">
          <li>Upload a clear, text-based PDF for best parsing results. Scanned image PDFs may produce less accurate results.</li>
          <li>Write a detailed job description — the AI uses it to generate relevant questions and score answers.</li>
          <li>Use the <strong>Stage</strong> dropdown immediately after each interview round to keep the pipeline current.</li>
          <li>The <strong>Dashboard</strong> updates in real-time as you complete interviews and change stages.</li>
          <li>You can <strong>re-interview</strong> a candidate by opening their report and clicking "Re-interview".</li>
          <li>Update the <strong>Experience (yrs)</strong> and <strong>Category</strong> inline in the table if the AI parsed them incorrectly.</li>
        </ul>
      </Section>

      {/* ── FAQ ───────────────────────────────────────────────────────────── */}
      <Section title="Frequently Asked Questions">
        <QA q="Can I upload a DOCX resume?">
          Yes. The system accepts PDF, DOCX, and plain TXT files. DOCX files are parsed with
          full text extraction including headers and body content.
        </QA>
        <QA q="What happens if I reject a candidate?">
          Setting a candidate's stage to <strong>Rejected</strong> marks them visually in the Interviews
          table (dimmed row). Their record and report are preserved — rejection can be undone by
          selecting a different stage.
        </QA>
        <QA q="Can multiple HR managers use the app at the same time?">
          Yes. All data is stored in a shared PostgreSQL database, so any logged-in user
          sees the same candidates, interviews, and pipeline state.
        </QA>
        <QA q="How do I change pipeline stage names?">
          Go to <strong>Settings</strong> in the sidebar. Under Pipeline Stages, edit any label and
          click Save Settings. Changes reflect immediately across the entire app.
        </QA>
        <QA q="Are interview reports saved permanently?">
          Yes. Reports are stored in the database and can be accessed anytime via
          the Interviews table → View Report.
        </QA>
        <QA q="How is the overall score calculated?">
          Each answer is scored by GPT-4.1-mini based on the question context, job description,
          and candidate's resume. The overall score is a weighted average across all questions.
        </QA>
      </Section>

    </div>
  );
}
