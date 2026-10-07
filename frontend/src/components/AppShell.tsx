import {
  BookOpen,
  ChartColumn,
  Dumbbell,
  FlaskConical,
  Gamepad2,
  House,
  LogOut,
  Menu,
  MessageCircle,
  Settings,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth, useLearner } from "../context/AuthContext";
import { LetterTiles } from "./Tiles";

const NAV = [
  { to: "/", label: "Home", icon: House, end: true },
  { to: "/practice", label: "Practice", icon: Dumbbell },
  { to: "/lexi", label: "Ask Lexi", icon: MessageCircle },
  { to: "/read", label: "Reading room", icon: BookOpen },
  { to: "/word-lab", label: "Word lab", icon: FlaskConical },
  { to: "/games", label: "Games", icon: Gamepad2 },
  { to: "/progress", label: "Progress", icon: ChartColumn },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  const { user, setActiveLearner, signOut } = useAuth();
  const learner = useLearner();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <header className="topbar">
        <span className="brand" aria-label="LexiLearn">
          <LetterTiles word="Lexi" size="sm" />
        </span>
        <button
          type="button"
          className="btn-icon"
          aria-expanded={menuOpen}
          aria-controls="main-nav"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={24} /> : <Menu size={24} />}
          <span className="visually-hidden">Menu</span>
        </button>
      </header>

      <nav id="main-nav" className={menuOpen ? "sidebar sidebar-open" : "sidebar"} aria-label="Main">
        <span className="brand brand-side" aria-label="LexiLearn">
          <LetterTiles word="Lexi" size="sm" />
        </span>

        {user && user.learners.length > 1 ? (
          <label className="learner-switch">
            <span>Learner</span>
            <select value={learner.id} onChange={(e) => setActiveLearner(e.target.value)}>
              {user.learners.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="learner-name">Reading with {learner.name}</p>
        )}

        <ul className="nav-list">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <li key={to}>
              <NavLink to={to} end={end} className="nav-link" onClick={() => setMenuOpen(false)}>
                <Icon size={22} aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>

        <button type="button" className="nav-link nav-signout" onClick={() => void signOut()}>
          <LogOut size={22} aria-hidden="true" />
          Sign out
        </button>
      </nav>

      <main id="main" className="content" tabIndex={-1}>
        <Outlet />
      </main>
    </div>
  );
}
