import logo from "../assets/tech9labs_logo.png";

export default function Header() {
  return (
    <header className="header">
      <img src={logo} className="logo" alt="Tech9Labs" />
      <div>
        <h1>Resume Intelligence</h1>
        <div className="subtitle">AI-powered resume shortlisting</div>
      </div>
    </header>
  );
}
