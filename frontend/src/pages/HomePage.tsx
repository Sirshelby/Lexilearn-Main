import { BookOpen, Clock, Flame, Gamepad2, MessageCircle, Trophy } from "lucide-react";
import { Link } from "react-router-dom";
import { ErrorNote, Loading } from "../components/Feedback";
import { SpeakButton } from "../components/SpeakButton";
import { SyllableTiles } from "../components/Tiles";
import { useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { useProgress, useWordAnalysis, wordOfTheDay } from "../lib/useProgress";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function HomePage() {
  const learner = useLearner();
  const { say } = usePreferences();
  const progress = useProgress();
  const skill = progress.data?.current_skill ?? null;
  const todaysWord = wordOfTheDay(skill?.words ?? []);
  const analysis = useWordAnalysis(todaysWord);

  if (progress.isPending) return <Loading />;
  if (progress.error) return <ErrorNote error={progress.error} />;
  const p = progress.data;

  return (
    <div className="page home">
      <h1>
        {greeting()}, {learner.name}
      </h1>

      <section className="today" aria-labelledby="today-title">
        {skill ? (
          <>
            <div className="today-word">
              {analysis.data ? (
                <SyllableTiles syllables={analysis.data.syllables} size="lg" onSyllable={(s) => void say(s)} />
              ) : (
                <span className="tiles-placeholder" />
              )}
              {todaysWord && <SpeakButton text={todaysWord} label="Hear today's word" />}
            </div>
            <div className="today-skill">
              <h2 id="today-title">
                Level {skill.level}: {skill.title}
              </h2>
              <p>{skill.focus}</p>
              <p className="tip">{skill.tip}</p>
              <Link to="/practice" className="btn btn-large">
                Start practice
              </Link>
            </div>
          </>
        ) : (
          <div className="today-skill">
            <h2 id="today-title">You've finished every skill</h2>
            <p>That's all 8 levels. The reading room has stories at every level to keep your reading strong.</p>
            <Link to="/read" className="btn btn-large">
              Read a story
            </Link>
          </div>
        )}
      </section>

      <ul className="facts" aria-label="This week">
        <li>
          <Flame size={22} aria-hidden="true" />
          {p.streak_days > 0 ? (
            <span>
              <strong>{p.streak_days}</strong> {p.streak_days === 1 ? "day" : "days"} in a row
            </span>
          ) : (
            <span>Start a streak today</span>
          )}
        </li>
        <li>
          <Clock size={22} aria-hidden="true" />
          <span>
            <strong>{p.minutes_this_week}</strong> minutes this week
          </span>
        </li>
        <li>
          <Trophy size={22} aria-hidden="true" />
          <span>
            <strong>{p.skills_mastered}</strong> of {p.total_skills} skills mastered
          </span>
        </li>
      </ul>

      {p.recommendations.length > 0 && (
        <section aria-labelledby="next-title">
          <h2 id="next-title">What to do next</h2>
          <ul className="next-steps">
            {p.recommendations.map((rec) => (
              <li key={rec}>{rec}</li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="more-title">
        <h2 id="more-title">Something different</h2>
        <ul className="link-list">
          <li>
            <Link to="/lexi">
              <MessageCircle size={22} aria-hidden="true" />
              <span>
                <strong>Ask Lexi</strong>
                <span className="hint">Get help with any word, step by step.</span>
              </span>
            </Link>
          </li>
          <li>
            <Link to="/read">
              <BookOpen size={22} aria-hidden="true" />
              <span>
                <strong>Read a story</strong>
                <span className="hint">Short stories that only use sounds you know.</span>
              </span>
            </Link>
          </li>
          <li>
            <Link to="/games">
              <Gamepad2 size={22} aria-hidden="true" />
              <span>
                <strong>Play a word game</strong>
                <span className="hint">Build words from syllables or catch rhymes.</span>
              </span>
            </Link>
          </li>
        </ul>
      </section>
    </div>
  );
}
