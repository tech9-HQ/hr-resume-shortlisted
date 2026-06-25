import { createContext, useContext, useState, useEffect } from "react";
import { getSettings, saveSettings } from "../api/client";

export const DEFAULT_SETTINGS = {
  stages: [
    { value: "hr_prescreening", label: "HR Pre-Screening", color: "#0ea5e9" },
    { value: "technical_1",     label: "Technical 1",      color: "#7c3aed" },
    { value: "technical_2",     label: "Technical 2",      color: "#6366f1" },
    { value: "management",      label: "Management",       color: "#f59e0b" },
    { value: "final_hr",        label: "Final HR Round",   color: "#16a34a" },
    { value: "rejected",        label: "Rejected",         color: "#dc2626" },
  ],
  categories: ["Sales", "Pre-Sales", "Technical", "Admin", "Management", "Finance", "Others"],
};

const SettingsContext = createContext(null);

export function SettingsProvider({ children }) {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [loaded, setLoaded]     = useState(false);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .catch(() => {})
      .finally(() => setLoaded(true));
  }, []);

  const updateSettings = async (next) => {
    setSettings(next);
    await saveSettings(next);
  };

  return (
    <SettingsContext.Provider value={{ settings, updateSettings, loaded }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  return useContext(SettingsContext);
}
