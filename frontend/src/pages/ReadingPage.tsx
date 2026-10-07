import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { ErrorNote, Loading } from "../components/Feedback";
import { TappableText } from "../components/TappableText";
import { useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { api } from "../lib/api";
import { readAlong } from "../lib/speech";
import type { Passage } from "../lib/types";
import { useProgress } from "../lib/useProgress";

export function ReadingPage() {
  const learner = useLearner();
  const { prefs } = usePreferences();
  const progress = useProgress();
  const maxLevel = progress.data?.current_level ?? 1;

  const [passage, setPassage] = useState<Passage | null>(null);
  const [level, setLevel] = useState<number | null>(null);
  const [topic, setTopic] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [spokenAt, setSpokenAt] = useState<number | null>(null);
  const [reading, setReading] = useState(false);
  const stopRef = useRef<(() => void) | null>(null);

  async function load(withTopic?: string, atLevel?: number) {
    stopRef.current?.();
    setBusy(true);
    setError(null);
    try {
      setPassage(await api.passage(learner.id, withTopic, atLevel ?? level ?? undefined));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void load();
    return () => stopRef.current?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learner.id]);

  function toggleReading() {
    if (!passage) return;
    if (reading) {
      stopRef.current?.();
      return;
    }
    setReading(true);
    stopRef.current = readAlong(passage.text, prefs.speech_rate * 0.9, setSpokenAt, () => {
      setReading(false);
      setSpokenAt(null);
      stopRef.current = null;
    });
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void load(topic.trim() || undefined);
  }

  return (
    <div className="page reading">
      <h1>Reading room</h1>

      <form className="reading-controls" onSubmit={submit}>
        <div className="field">
          <label htmlFor="topic">Make a new story about</label>
          <input id="topic" value={topic} maxLength={60} onChange={(e) => setTopic(e.target.value)}
            placeholder="a dog, the beach, football..." />
        </div>
        <div className="field">
          <label htmlFor="level">Level</label>
          <select id="level" value={level ?? maxLevel} onChange={(e) => {
            const next = Number(e.target.value);
            setLevel(next);
            void load(undefined, next);
          }}>
            {Array.from({ length: maxLevel }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                Level {n}
              </option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Writing" : "Get a story"}
        </button>
      </form>

      {error !== null && <ErrorNote error={error} />}
      {busy && !passage && <Loading label="Finding a story" />}

      {passage && (
        <article className="passage" aria-busy={busy}>
          <h2>{passage.title}</h2>
          {passage.tricky_words.length > 0 && (
            <p className="hint">Words to look at first: {passage.tricky_words.join(", ")}</p>
          )}
          <TappableText text={passage.text} highlightAt={spokenAt} className="passage-text" />
          <div className="row">
            <button type="button" className="btn" onClick={toggleReading}>
              {reading ? <Pause size={20} aria-hidden="true" /> : <Play size={20} aria-hidden="true" />}
              {reading ? "Stop" : "Read it to me"}
            </button>
            <span className="hint">Tap any word to hear it on its own.</span>
          </div>
          <p className="source">
            {passage.source === "generated"
              ? `Lexi wrote this story for you. Every word was checked, and ${Math.round(passage.score)}% use sounds you've learned.`
              : "From the LexiLearn story library."}
          </p>
        </article>
      )}
    </div>
  );
}
