import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ErrorNote } from "../components/Feedback";
import { SpeakButton } from "../components/SpeakButton";
import { SyllableLegend, SyllableTiles } from "../components/Tiles";
import { usePreferences } from "../context/PreferencesContext";
import { api } from "../lib/api";
import { useProgress } from "../lib/useProgress";
import { tokenize } from "../lib/words";

const BAND_TEXT = {
  independent: "Comfortable to read alone.",
  with_support: "Readable with an adult nearby to help with a few words.",
  too_hard: "Too many unfamiliar patterns for this level right now.",
} as const;

function WordExplorer() {
  const { say } = usePreferences();
  const [word, setWord] = useState("");
  const analysis = useMutation({ mutationFn: (w: string) => api.analyzeWord(w) });

  function submit(event: FormEvent) {
    event.preventDefault();
    const clean = word.trim().toLowerCase();
    if (/^[a-z']+$/.test(clean)) analysis.mutate(clean);
  }

  const data = analysis.data;
  return (
    <section aria-labelledby="explore-title" className="stack">
      <h2 id="explore-title">Break a word apart</h2>
      <form onSubmit={submit} className="inline-form">
        <label htmlFor="lab-word" className="visually-hidden">
          Word
        </label>
        <input id="lab-word" value={word} onChange={(e) => setWord(e.target.value)} maxLength={40}
          placeholder="Type a word, like sunset" autoCapitalize="off" spellCheck={false} />
        <button type="submit" className="btn" disabled={analysis.isPending}>
          Show me
        </button>
      </form>
      {analysis.error && <ErrorNote error={analysis.error} />}
      {data && (
        <div className="stage stack">
          <SyllableTiles syllables={data.syllables} size="lg" showLabels onSyllable={(s) => void say(s, { slow: true })} />
          <div className="row">
            <SpeakButton text={data.word} />
            <SpeakButton text={data.word} label="Slowly" slow />
          </div>
          <p>
            {data.syllables.length} syllable{data.syllables.length === 1 ? "" : "s"}
            {data.sound_count ? ` and ${data.sound_count} sounds` : ""}.{" "}
            {data.required_level === null
              ? "It doesn't follow the usual patterns, so it's learned by heart."
              : `It can be sounded out from level ${data.required_level}.`}
            {data.heart_word_level !== null && ` It's also a heart word from level ${data.heart_word_level}.`}
          </p>
          {data.patterns.length > 0 && (
            <>
              <h3>Patterns in this word</h3>
              <ul className="pattern-list">
                {data.patterns.map((p) => (
                  <li key={p}>{p}</li>
                ))}
              </ul>
            </>
          )}
          <SyllableLegend />
        </div>
      )}
    </section>
  );
}

function PassageChecker() {
  const progress = useProgress();
  const [text, setText] = useState("");
  const [level, setLevel] = useState<number>(progress.data?.current_level ?? 1);
  const check = useMutation({ mutationFn: () => api.checkText(text, level) });
  const report = check.data;
  const tricky = new Set(report?.tricky_words ?? []);

  return (
    <section aria-labelledby="check-title" className="stack">
      <h2 id="check-title">Check a reading passage</h2>
      <p className="muted">
        For parents and teachers. Paste a text to see how much of it a learner can sound out at a given level.
      </p>
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim()) check.mutate();
        }}
      >
        <label htmlFor="passage" className="visually-hidden">
          Passage
        </label>
        <textarea id="passage" rows={6} maxLength={5000} value={text} onChange={(e) => setText(e.target.value)}
          placeholder="Paste a page from a book or worksheet" />
        <div className="inline-form">
          <label htmlFor="check-level">Level</label>
          <select id="check-level" value={level} onChange={(e) => setLevel(Number(e.target.value))}>
            {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <option key={n} value={n}>
                Level {n}
              </option>
            ))}
          </select>
          <button type="submit" className="btn" disabled={check.isPending}>
            Check passage
          </button>
        </div>
      </form>
      {check.error && <ErrorNote error={check.error} />}
      {report && (
        <div className="stage stack" aria-live="polite">
          <p className={`score score-${report.band}`}>
            <strong>{Math.round(report.score)}%</strong> decodable at level {report.level}. {BAND_TEXT[report.band]}
          </p>
          <p className="checked-text">
            {tokenize(text).map((seg, i) =>
              seg.isWord && tricky.has(seg.text.toLowerCase()) ? (
                <mark key={i} className="word-tricky">
                  {seg.text}
                </mark>
              ) : (
                <span key={i}>{seg.text}</span>
              ),
            )}
          </p>
          {report.tricky_words.length > 0 && (
            <p className="hint">Words to teach first: {report.tricky_words.slice(0, 20).join(", ")}</p>
          )}
        </div>
      )}
    </section>
  );
}

export function WordLabPage() {
  return (
    <div className="page">
      <h1>Word lab</h1>
      <WordExplorer />
      <PassageChecker />
    </div>
  );
}
