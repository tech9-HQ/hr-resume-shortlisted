import { useSettings } from "../context/SettingsContext";

const FEATURES = [
  {
    icon: "📄",
    title: "Resume Parsing",
    desc: "Upload any PDF or DOCX resume. The system automatically extracts name, contact info, skills, years of experience, and categorises the candidate.",
  },
  {
    icon: "🤖",
    title: "AI Interview Questions",
    desc: "GPT-4 reads the resume and job description together, then generates tailored questions across 5 types: Introduction, Background, Technical, Behavioral, and Logistics.",
  },
  {
    icon: "⭐",
    title: "Answer Scoring",
    desc: "Rate each answer 1–5 stars during the interview. The AI evaluates all answers in context and produces an overall score from 0–100 with a Hire / Maybe / No recommendation.",
  },
  {
    icon: "📊",
    title: "Interview Report",
    desc: "A full PDF-ready report is generated after every interview — summary, strengths, concerns, per-question feedback, and an overall recommendation.",
  },
  {
    icon: "🔄",
    title: "Pipeline Tracking",
    desc: "Move candidates through configurable hiring stages (HR Pre-Screening → Technical 1 → Management → Final HR Round) or mark as Rejected at any point.",
  },
  {
    icon: "📈",
    title: "Dashboard Analytics",
    desc: "Real-time charts show hiring pipeline health, score distribution, category breakdown, and recent interview activity across your whole team.",
  },
];

const WORKFLOW = [
  { label: "Upload Resume",     icon: "📤", desc: "PDF or DOCX" },
  { label: "AI Generates Qs",  icon: "🤖", desc: "Tailored to JD" },
  { label: "Conduct Interview", icon: "🎤", desc: "Rate & note answers" },
  { label: "Get AI Report",     icon: "📋", desc: "Score + recommendation" },
  { label: "Track Pipeline",    icon: "🔄", desc: "Move through stages" },
];

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
        <h1 className="help-title">Pre Screening Assistant — User Guide</h1>
        <p className="help-sub">Everything you need to use the Pre Screening Assistant effectively.</p>
      </div>

      {/* ── What is this tool ─────────────────────────────────────────────── */}
      <Section title="What is Pre Screening Assistant?">
        <p className="help-overview-text">
          Pre Screening Assistant is an AI-powered HR tool built by <strong>Tech9Labs</strong> that
          helps your team run structured, consistent pre-screening interviews at scale. Instead of
          spending hours crafting interview questions and writing up notes, the tool reads a
          candidate's resume and the job description, auto-generates relevant questions, guides the
          interviewer through the session, and produces a scored report — all in under 10 minutes.
        </p>
        <p className="help-overview-text" style={{ marginTop: 10 }}>
          All interview data is stored centrally, so every HR manager on your team sees the same
          candidate records, pipeline stages, and reports in real time.
        </p>

        {/* Workflow strip */}
        <div className="help-workflow">
          {WORKFLOW.map((step, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 0 }}>
              <div className="help-workflow-step">
                <div className="help-workflow-icon">{step.icon}</div>
                <div className="help-workflow-label">{step.label}</div>
                <div className="help-workflow-desc">{step.desc}</div>
              </div>
              {i < WORKFLOW.length - 1 && (
                <div className="help-workflow-arrow">›</div>
              )}
            </div>
          ))}
        </div>
      </Section>

      {/* ── Key Features ─────────────────────────────────────────────────── */}
      <Section title="Key Features">
        <div className="help-features-grid">
          {FEATURES.map((f) => (
            <div key={f.title} className="help-feature-card">
              <div className="help-feature-icon">{f.icon}</div>
              <div className="help-feature-title">{f.title}</div>
              <div className="help-feature-desc">{f.desc}</div>
            </div>
          ))}
        </div>
      </Section>

      {/* ── Who is it for ────────────────────────────────────────────────── */}
      <Section title="Who is this tool for?">
        <div className="help-roles">
          <div className="help-role-card">
            <div className="help-role-title">👩‍💼 HR Managers</div>
            <ul className="help-role-list">
              <li>Start and conduct AI-assisted pre-screening interviews</li>
              <li>View scores and recommendations before deciding next steps</li>
              <li>Move candidates through the hiring pipeline stages</li>
              <li>Reject candidates at any stage without losing their record</li>
            </ul>
          </div>
          <div className="help-role-card">
            <div className="help-role-title">🔍 Talent Acquisition</div>
            <ul className="help-role-list">
              <li>Filter candidates by category, score, or pipeline stage</li>
              <li>Compare interview reports across candidates for the same role</li>
              <li>Use the Dashboard to track overall hiring funnel health</li>
              <li>Download or print reports to share with hiring managers</li>
            </ul>
          </div>
          <div className="help-role-card">
            <div className="help-role-title">⚙️ Admins</div>
            <ul className="help-role-list">
              <li>Customise pipeline stage names and colours in Settings</li>
              <li>Manage candidate categories for your organisation</li>
              <li>Add or remove team members via Supabase Authentication</li>
            </ul>
          </div>
        </div>
      </Section>

      {/* ── Getting Started ───────────────────────────────────────────────── */}
      <Section title="Step-by-Step: Running Your First Interview">
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
