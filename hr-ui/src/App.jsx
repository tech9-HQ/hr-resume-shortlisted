import { useState } from "react";
import Header from "./components/Header";
import JDForm from "./components/JDForm";
import ShortlistResults from "./components/ShortlistResults";
import "./styles/theme.css";

export default function App() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  return (
    <div className="app-container">
      <Header />

      <JDForm
        onResults={setResults}
        setLoading={setLoading}
      />

      <ShortlistResults
        results={results}
        loading={loading}
      />
    </div>
  );
}
