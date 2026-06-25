import { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";
import { SettingsProvider } from "./context/SettingsContext";
import { getReport, fetchSession } from "./api/client";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import Login from "./components/Login";
import Dashboard from "./components/Dashboard";
import SessionHistory from "./components/SessionHistory";
import NewInterview from "./components/NewInterview";
import InterviewPortal from "./components/InterviewPortal";
import ReportCard from "./components/ReportCard";
import Settings from "./components/Settings";
import Help from "./components/Help";
import "./styles/theme.css";

// view: "dashboard" | "home" | "new-interview" | "interview" | "report" | "settings" | "help"

function AuthedApp({ user }) {
  const [view, setView]                     = useState("dashboard");
  const [currentSession, setCurrentSession] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [interviewResult, setInterviewResult] = useState(null);

  const handleSessionStarted = (session) => {
    setCurrentSession(session);
    setSelectedCandidate(session.candidate);
    setView("interview");
  };

  const handleContinue = async (historyRow) => {
    try {
      const session = await fetchSession(historyRow.session_id);
      const candidate = session.candidates?.[0];
      if (!candidate) return;
      setCurrentSession(session);
      setSelectedCandidate(candidate);
      setView("interview");
    } catch {
      alert("Could not load session. Please try again.");
    }
  };

  const handleViewReport = async (historyRow) => {
    try {
      const report = await getReport(historyRow.candidate_id, historyRow.session_id);
      setCurrentSession({ session_id: historyRow.session_id, position_title: historyRow.position_title });
      setSelectedCandidate({
        candidate_id: historyRow.candidate_id,
        name: historyRow.candidate_name,
        email: historyRow.candidate_email,
        experience: historyRow.experience,
        category: historyRow.category,
      });
      setInterviewResult(report);
      setView("report");
    } catch {
      alert("Report not found. The interview may not have been completed.");
    }
  };

  const handleInterviewComplete = (result) => {
    setInterviewResult(result);
    setView("report");
  };

  const handleSidebarNavigate = (target) => {
    if (view === "interview") return;
    setView(target);
  };

  const showSidebar = !["interview", "report"].includes(view);

  return (
    <div className="app-shell">
      {showSidebar && (
        <Sidebar currentView={view} onNavigate={handleSidebarNavigate} user={user} />
      )}
      <div className={`app-main${showSidebar ? "" : " app-main--full"}`}>
        <Header />

        {view === "dashboard"    && <Dashboard />}
        {view === "settings"     && <Settings />}
        {view === "help"         && <Help />}

        {view === "home" && (
          <SessionHistory
            onNewInterview={() => setView("new-interview")}
            onContinue={handleContinue}
            onViewReport={handleViewReport}
          />
        )}
        {view === "new-interview" && (
          <NewInterview
            onStarted={handleSessionStarted}
            onCancel={() => setView("home")}
          />
        )}
        {view === "interview" && selectedCandidate && currentSession && (
          <InterviewPortal
            candidate={selectedCandidate}
            session={currentSession}
            onComplete={handleInterviewComplete}
            onBack={() => setView("home")}
          />
        )}
        {view === "report" && interviewResult && selectedCandidate && currentSession && (
          <ReportCard
            result={interviewResult}
            candidate={selectedCandidate}
            session={currentSession}
            onBack={() => setView("home")}
            onReInterview={() => setView("interview")}
          />
        )}
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  if (user === undefined) {
    return (
      <div className="auth-loading">
        <div className="auth-spinner" />
      </div>
    );
  }

  if (user === null) return <Login />;

  return (
    <SettingsProvider>
      <AuthedApp user={user} />
    </SettingsProvider>
  );
}
