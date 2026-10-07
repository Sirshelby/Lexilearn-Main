import { useQueries, useQuery } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Loading } from "../../components/Feedback";
import { SpeakButton } from "../../components/SpeakButton";
import { LetterTiles } from "../../components/Tiles";
import { usePreferences } from "../../context/PreferencesContext";
import { api } from "../../lib/api";
import { shuffle } from "../../lib/words";

const ROUNDS = 6;
// Skills whose words have two or more syllables. 5.1 (two closed syllables)
// only uses short vowels, so it's fine for learners below level 5 as well.
const SKILL_CODES = ["5.1", "5.2", "5.3", "8.1"];

interface Piece {
  id: number;
  text: string;
}

export function SyllableBuilder({ maxLevel }: { maxLevel: number }) {
  const { say } = usePreferences();
  const curriculum = useQuery({ queryKey: ["curriculum"], queryFn: api.curriculum, staleTime: Infinity });

  const words = useMemo(() => {
    const skills = curriculum.data?.levels.flatMap((l) => l.skills) ?? [];
    const allowed = skills.filter(
      (s) => SKILL_CODES.includes(s.code) && (s.code === "5.1" || s.level <= maxLevel),
    );
    return shuffle(allowed.flatMap((s) => s.words)).slice(0, ROUNDS);
  }, [curriculum.data, maxLevel]);

  const analyses = useQueries({
    queries: words.map((w) => ({
      queryKey: ["word", w],
      queryFn: () => api.analyzeWord(w),
      staleTime: Infinity,
    })),
  });

  const [round, setRound] = useState(0);
  const [placed, setPlaced] = useState<Piece[]>([]);
  const [score, setScore] = useState(0);
  const [status, setStatus] = useState<"building" | "right" | "wrong">("building");

  const target = words[round];
  const syllables = analyses[round]?.data?.syllables.map((s) => s.text);
  const pieces = useMemo(
    () => shuffle((syllables ?? []).map((text, id) => ({ id, text }))),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [round, syllables?.join("-")],
  );

  useEffect(() => {
    if (target) void say(target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  if (curriculum.isPending || (target && !syllables)) return <Loading />;

  if (round >= words.length) {
    return (
      <div className="stage stack">
        <h2>
          You built {score} of {words.length} words
        </h2>
        <button type="button" className="btn" onClick={() => { setRound(0); setScore(0); setPlaced([]); }}>
          <RotateCcw size={20} aria-hidden="true" /> Play again
        </button>
      </div>
    );
  }

  function place(piece: Piece) {
    if (status !== "building" || !syllables) return;
    const next = [...placed, piece];
    setPlaced(next);
    void say(piece.text);
    if (next.length === syllables.length) {
      const right = next.map((p) => p.text).join("") === target;
      setStatus(right ? "right" : "wrong");
      if (right) {
        setScore((s) => s + 1);
        void say(target!);
      }
    }
  }

  function advance() {
    setPlaced([]);
    setStatus("building");
    setRound((r) => r + 1);
  }

  return (
    <div className="stage stack">
      <p className="hint">
        Word {round + 1} of {words.length}. Listen, then tap the parts in order.
      </p>
      <SpeakButton text={target!} label="Hear the word" />

      <div className={`build-slots build-${status}`} aria-live="polite">
        {syllables!.map((_, i) => (
          <span key={i} className="slot">
            {placed[i] ? <LetterTiles word={placed[i]!.text} size="md" /> : <span className="slot-empty" />}
          </span>
        ))}
      </div>

      <div className="piece-tray">
        {pieces.map((piece) => (
          <button key={piece.id} type="button" className="piece" disabled={placed.some((p) => p.id === piece.id)}
            onClick={() => place(piece)} aria-label={piece.text}>
            <LetterTiles word={piece.text} size="md" />
          </button>
        ))}
      </div>

      {status === "right" && <p className="note note-good">Yes, {target}!</p>}
      {status === "wrong" && (
        <p className="note note-warn">
          Not quite. It's {syllables!.join("-")}. Clap it out: {syllables!.length} parts.
        </p>
      )}
      <div className="row">
        {status === "wrong" && (
          <button type="button" className="btn btn-quiet" onClick={() => { setPlaced([]); setStatus("building"); }}>
            Try again
          </button>
        )}
        {status !== "building" && (
          <button type="button" className="btn" onClick={advance}>
            Next word
          </button>
        )}
      </div>
    </div>
  );
}
