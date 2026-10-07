import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Lightbulb, RotateCcw } from "lucide-react";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ErrorNote, Loading } from "../components/Feedback";
import { useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { ItemView, SyllableChunks } from "../features/practice/items";
import { api } from "../lib/api";
import type { AnswerResult, CompleteResult, PracticeSession, Skill } from "../lib/types";
import { useProgress } from "../lib/useProgress";

type Phase =
  | { name: "intro" }
  | { name: "running"; session: PracticeSession; index: number; result: AnswerResult | null; correct: number }
  | { name: "done"; session: PracticeSession; result: CompleteResult };

function useSkill(code: string | null): Skill | null {
  const progress = useProgress();
  const curriculum = useQuery({ queryKey: ["curriculum"], queryFn: api.curriculum, staleTime: Infinity });
  if (!code) return progress.data?.current_skill ?? null;
  return curriculum.data?.levels.flatMap((l) => l.skills).find((s) => s.code === code) ?? null;
}

export function PracticePage() {
  const learner = useLearner();
  const queryClient = useQueryClient();
  const { say } = usePreferences();
  const [params] = useSearchParams();
  const skillCode = params.get("skill");
  const skill = useSkill(skillCode);

  const [phase, setPhase] = useState<Phase>({ name: "intro" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function run<T>(task: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await task();
    } catch (err) {
      setError(err);
      return undefined;
    } finally {
      setBusy(false);
    }
  }

  async function start() {
    const session = await run(() => api.startPractice(learner.id, skillCode ?? undefined));
    if (session) setPhase({ name: "running", session, index: 0, result: null, correct: 0 });
  }

  async function answer(value: string) {
    if (phase.name !== "running" || phase.result) return;
    const item = phase.session.items[phase.index];
    if (!item) return;
    const result = await run(() => api.answer(learner.id, phase.session.id, item.index, value));
    if (!result) return;
    setPhase({ ...phase, result, correct: phase.correct + (result.correct ? 1 : 0) });
    void say(result.correct ? "Yes!" : (result.syllables ?? []).join(" "));
  }

  async function next() {
    if (phase.name !== "running") return;
    if (phase.index + 1 < phase.session.items.length) {
      setPhase({ ...phase, index: phase.index + 1, result: null });
      return;
    }
    const result = await run(() => api.completePractice(learner.id, phase.session.id));
    if (result) {
      setPhase({ name: "done", session: phase.session, result });
      void queryClient.invalidateQueries({ queryKey: ["progress", learner.id] });
    }
  }

  if (phase.name === "intro") {
    if (!skill) return <Loading />;
    return (
      <div className="page practice">
        <h1>Practice</h1>
        <section className="stage stack">
          <h2>
            Level {skill.level}: {skill.title}
          </h2>
          <p>{skill.focus}</p>
          <p className="tip">
            <Lightbulb size={20} aria-hidden="true" /> {skill.tip}
          </p>
          <p className="hint">8 short questions. Turn your sound on, some of them are spoken.</p>
          {error !== null && <ErrorNote error={error} />}
          <button type="button" className="btn btn-large" onClick={() => void start()} disabled={busy}>
            {busy ? "Getting ready" : "Start"}
          </button>
        </section>
      </div>
    );
  }

  if (phase.name === "done") {
    const { result } = phase;
    return (
      <div className="page practice">
        <h1>Practice</h1>
        <section className="stage stack" aria-live="polite">
          <h2>
            {result.correct} out of {result.total}
          </h2>
          {result.mastered_now ? (
            <p className="note note-good">
              <CircleCheck size={22} aria-hidden="true" /> You've mastered {phase.session.skill_title}. On to the
              next skill!
            </p>
          ) : (
            <p>
              {result.accuracy >= 85
                ? "Strong work. A couple more sessions like that and this skill is yours."
                : "Every session makes the sounds stick a bit more. Try again, or ask Lexi about a tricky word."}
            </p>
          )}
          <div className="row">
            <button type="button" className="btn" onClick={() => setPhase({ name: "intro" })}>
              <RotateCcw size={20} aria-hidden="true" /> Practise again
            </button>
            <Link to="/" className="btn btn-quiet">
              Back to home
            </Link>
          </div>
        </section>
      </div>
    );
  }

  const item = phase.session.items[phase.index]!;
  const total = phase.session.items.length;

  return (
    <div className="page practice">
      <h1 className="visually-hidden">Practice: {phase.session.skill_title}</h1>
      <ol className="dots" aria-label={`Question ${phase.index + 1} of ${total}`}>
        {phase.session.items.map((it) => (
          <li
            key={it.index}
            className={it.index < phase.index ? "dot dot-done" : it.index === phase.index ? "dot dot-now" : "dot"}
          />
        ))}
      </ol>

      <section className="stage stack" aria-labelledby="item-prompt">
        <h2 id="item-prompt">{item.prompt}</h2>
        <ItemView key={item.index} item={item} onAnswer={(v) => void answer(v)} disabled={busy || phase.result !== null}
          result={phase.result} />

        {phase.result && (
          <div className={phase.result.correct ? "note note-good" : "note note-warn"} aria-live="polite">
            <p>{phase.result.feedback}</p>
            {phase.result.syllables && <SyllableChunks syllables={phase.result.syllables} />}
          </div>
        )}
        {error !== null && <ErrorNote error={error} />}

        {phase.result && (
          <button type="button" className="btn btn-large" onClick={() => void next()} disabled={busy} autoFocus>
            {phase.index + 1 < total ? "Next question" : "Finish"}
          </button>
        )}
      </section>
    </div>
  );
}
