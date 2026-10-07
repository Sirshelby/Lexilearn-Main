import { Trash2 } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";
import { ErrorNote } from "../components/Feedback";
import { SpeakButton } from "../components/SpeakButton";
import { LetterTiles } from "../components/Tiles";
import { useAuth, useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { api } from "../lib/api";
import type { Font, Overlay, ReadingPreferences, Theme } from "../lib/types";
import { AGE_BANDS } from "./RegisterPage";

const FONTS: { value: Font; label: string; family: string }[] = [
  { value: "lexend", label: "Lexend", family: "Lexend" },
  { value: "atkinson", label: "Atkinson Hyperlegible", family: "Atkinson Hyperlegible" },
  { value: "opendyslexic", label: "OpenDyslexic", family: "OpenDyslexic" },
  { value: "system", label: "My device's font", family: "system-ui" },
];
const THEMES: { value: Theme; label: string }[] = [
  { value: "soft", label: "Soft grey" },
  { value: "cream", label: "Cream" },
  { value: "dark", label: "Dark" },
  { value: "high_contrast", label: "High contrast" },
];
const OVERLAYS: { value: Overlay; label: string }[] = [
  { value: "none", label: "None" },
  { value: "blue", label: "Blue" },
  { value: "yellow", label: "Yellow" },
  { value: "green", label: "Green" },
  { value: "rose", label: "Rose" },
  { value: "peach", label: "Peach" },
];

function Options<T extends string>({ legend, name, value, options, onChange, render }: {
  legend: string;
  name: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (value: T) => void;
  render?: (option: { value: T; label: string }) => ReactNode;
}) {
  return (
    <fieldset className="options">
      <legend>{legend}</legend>
      {options.map((option) => (
        <label key={option.value} className={value === option.value ? "option option-on" : "option"}>
          <input type="radio" name={name} value={option.value} checked={value === option.value}
            onChange={() => onChange(option.value)} />
          {render ? render(option) : option.label}
        </label>
      ))}
    </fieldset>
  );
}

function ReadingSettings() {
  const { prefs, update, saving } = usePreferences();
  const set = <K extends keyof ReadingPreferences>(key: K) => (value: ReadingPreferences[K]) => update({ [key]: value });

  return (
    <section aria-labelledby="reading-settings" className="settings-grid">
      <div className="stack">
        <h2 id="reading-settings">Reading</h2>
        <p className="hint" aria-live="polite">{saving ? "Saving" : "Changes save automatically."}</p>

        <Options legend="Font" name="font" value={prefs.font} options={FONTS} onChange={set("font")}
          render={(o) => <span style={{ fontFamily: FONTS.find((f) => f.value === o.value)?.family }}>{o.label}</span>} />

        <div className="field">
          <label htmlFor="text-size">Text size: {prefs.text_size}px</label>
          <input id="text-size" type="range" min={16} max={32} step={1} value={prefs.text_size}
            onChange={(e) => update({ text_size: Number(e.target.value) })} />
        </div>

        <Options legend="Space between letters" name="letter_spacing" value={prefs.letter_spacing}
          options={[{ value: "normal", label: "Normal" }, { value: "wide", label: "Wide" }, { value: "wider", label: "Wider" }]}
          onChange={set("letter_spacing")} />
        <Options legend="Space between lines" name="line_spacing" value={prefs.line_spacing}
          options={[{ value: "normal", label: "Normal" }, { value: "relaxed", label: "Relaxed" }, { value: "loose", label: "Loose" }]}
          onChange={set("line_spacing")} />
        <Options legend="Background" name="theme" value={prefs.theme} options={THEMES} onChange={set("theme")} />
        <Options legend="Coloured overlay" name="overlay" value={prefs.overlay} options={OVERLAYS}
          onChange={set("overlay")}
          render={(o) => (
            <>
              <span className="swatch" data-overlay={o.value} aria-hidden="true" />
              {o.label}
            </>
          )} />

        <div className="field">
          <label htmlFor="speech-rate">Reading voice speed: {prefs.speech_rate.toFixed(1)}x</label>
          <input id="speech-rate" type="range" min={0.5} max={1.5} step={0.1} value={prefs.speech_rate}
            onChange={(e) => update({ speech_rate: Number(e.target.value) })} />
          <SpeakButton text="The cat sat on the mat." label="Test the voice" />
        </div>

        <label className="toggle">
          <input type="checkbox" checked={prefs.premium_voice} onChange={(e) => update({ premium_voice: e.target.checked })} />
          Use the clearer online voice when it's available
        </label>
        <label className="toggle">
          <input type="checkbox" checked={prefs.show_syllable_colours}
            onChange={(e) => update({ show_syllable_colours: e.target.checked })} />
          Show a colour under each kind of syllable
        </label>
      </div>

      <aside className="preview" aria-label="Preview">
        <LetterTiles word="sunset" size="md" />
        <p>The cat sat on the mat. Then it had a nap in the sun, and Sam sat with it.</p>
        <p className="hint">This preview updates as you change the settings.</p>
      </aside>
    </section>
  );
}

function Learners() {
  const { user, reloadUser, setActiveLearner } = useAuth();
  const active = useLearner();
  const [name, setName] = useState("");
  const [ageBand, setAgeBand] = useState("");
  const [error, setError] = useState<unknown>(null);

  if (!user) return null;
  const canAdd = user.account_type !== "learner";

  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const learner = await api.createLearner({
        name, age_band: ageBand || null, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      });
      await reloadUser();
      setActiveLearner(learner.id);
      setName("");
      setAgeBand("");
    } catch (err) {
      setError(err);
    }
  }

  async function remove(id: string, learnerName: string) {
    if (!window.confirm(`Delete ${learnerName}'s profile and all their progress? This can't be undone.`)) return;
    setError(null);
    try {
      await api.deleteLearner(id);
      await reloadUser();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <section aria-labelledby="learners-title" className="stack">
      <h2 id="learners-title">{canAdd ? "Learners" : "Profile"}</h2>
      <ul className="learner-list">
        {user.learners.map((l) => (
          <li key={l.id}>
            <span>
              <strong>{l.name}</strong>
              {l.age_band && <span className="hint"> age {l.age_band}</span>}
              {l.id === active.id && <span className="hint"> (reading now)</span>}
            </span>
            {canAdd && user.learners.length > 1 && (
              <button type="button" className="btn-icon" onClick={() => void remove(l.id, l.name)}
                aria-label={`Delete ${l.name}`}>
                <Trash2 size={18} />
              </button>
            )}
          </li>
        ))}
      </ul>
      {canAdd && (
        <form onSubmit={add} className="inline-form">
          <label htmlFor="new-learner" className="visually-hidden">First name</label>
          <input id="new-learner" placeholder="First name" value={name} maxLength={40} required
            onChange={(e) => setName(e.target.value)} />
          <label htmlFor="new-age" className="visually-hidden">Age</label>
          <select id="new-age" value={ageBand} onChange={(e) => setAgeBand(e.target.value)}>
            <option value="">Age (optional)</option>
            {AGE_BANDS.map((b) => <option key={b} value={b}>{b}</option>)}
          </select>
          <button type="submit" className="btn btn-quiet">Add learner</button>
        </form>
      )}
      {error !== null && <ErrorNote error={error} />}
    </section>
  );
}

export function SettingsPage() {
  const { user, signOut } = useAuth();
  const learner = useLearner();
  return (
    <div className="page">
      <h1>Settings for {learner.name}</h1>
      <ReadingSettings />
      <Learners />
      <section aria-labelledby="account-title" className="stack">
        <h2 id="account-title">Account</h2>
        <p>Signed in as {user?.email}</p>
        <button type="button" className="btn btn-quiet" onClick={() => void signOut()}>Sign out</button>
      </section>
    </div>
  );
}
