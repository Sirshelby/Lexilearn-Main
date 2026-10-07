import { Circle, CircleCheck, CircleDot, Lock } from "lucide-react";
import { Link } from "react-router-dom";
import { ErrorNote, Loading } from "../components/Feedback";
import type { ProgressSummary, SkillStatus } from "../lib/types";
import { useProgress } from "../lib/useProgress";

const STATUS_TEXT: Record<SkillStatus, string> = {
  mastered: "Mastered",
  in_progress: "In progress",
  available: "Up next",
  locked: "Not yet",
};

function StatusIcon({ status }: { status: SkillStatus }) {
  const props = { size: 22, "aria-hidden": true } as const;
  if (status === "mastered") return <CircleCheck {...props} className="status-mastered" />;
  if (status === "in_progress") return <CircleDot {...props} className="status-progress" />;
  if (status === "available") return <Circle {...props} className="status-progress" />;
  return <Lock {...props} className="status-locked" />;
}

function groupByLevel(skills: ProgressSummary["skills"]) {
  const levels = new Map<number, ProgressSummary["skills"]>();
  for (const skill of skills) {
    levels.set(skill.level, [...(levels.get(skill.level) ?? []), skill]);
  }
  return [...levels.entries()];
}

export function ProgressPage() {
  const { data, error, isPending } = useProgress();
  if (isPending) return <Loading />;
  if (error) return <ErrorNote error={error} />;

  const percent = Math.round((data.skills_mastered / data.total_skills) * 100);

  return (
    <div className="page">
      <h1>Progress</h1>
      <div className="overall">
        <p>
          <strong>{data.skills_mastered}</strong> of {data.total_skills} skills mastered. Working on level{" "}
          {data.current_level}: {data.level_title}.
        </p>
        <div className="meter" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}
          aria-label="Skills mastered">
          <span style={{ width: `${percent}%` }} />
        </div>
        <p className="hint">
          A skill is mastered after three practice sessions in a row that average 85% or better.
        </p>
      </div>

      {data.recent.length > 0 && (
        <section aria-labelledby="recent-title">
          <h2 id="recent-title">Recent practice</h2>
          <ul className="recent">
            {data.recent.map((session) => (
              <li key={session.completed_at}>
                <span>{session.skill_title}</span>
                <span className="bar" aria-hidden="true">
                  <span style={{ width: `${session.accuracy}%` }} />
                </span>
                <span>{Math.round(session.accuracy)}%</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section aria-labelledby="map-title">
        <h2 id="map-title">Skill map</h2>
        <ol className="skill-map">
          {groupByLevel(data.skills).map(([level, skills]) => (
            <li key={level} className="skill-level">
              <h3>Level {level}</h3>
              <ul>
                {skills.map((skill) => (
                  <li key={skill.code} className={`skill-row skill-${skill.status}`}>
                    <StatusIcon status={skill.status} />
                    <span className="skill-title">{skill.title}</span>
                    <span className="skill-meta">
                      {STATUS_TEXT[skill.status]}
                      {skill.accuracy !== null && `, ${Math.round(skill.accuracy)}% recently`}
                    </span>
                    {skill.status !== "locked" && (
                      <Link to={`/practice?skill=${skill.code}`} className="btn-text">
                        Practise
                      </Link>
                    )}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
