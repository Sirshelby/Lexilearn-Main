import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { SpeakButton } from "../../components/SpeakButton";
import { usePreferences } from "../../context/PreferencesContext";
import { rimeOf, shuffle } from "../../lib/words";

// Short-vowel word families. All of these are decodable at level 1.
const FAMILIES: string[][] = [
  ["cat", "hat", "mat", "sat", "bat", "rat"],
  ["pig", "dig", "big", "wig", "fig"],
  ["hop", "mop", "top", "pop"],
  ["bug", "rug", "hug", "mug", "jug"],
  ["hen", "ten", "pen", "men"],
  ["pet", "jet", "net", "wet", "get"],
  ["pin", "fin", "tin", "win"],
  ["hot", "pot", "dot", "got"],
];
const ROUNDS = 5;

function makeRound() {
  const [family, ...others] = shuffle(FAMILIES);
  const [target, ...rhymes] = shuffle(family!);
  const right = rhymes.slice(0, 3);
  const wrong = shuffle(others.flat()).slice(0, 3);
  return { target: target!, options: shuffle([...right, ...wrong]) };
}

export function RhymeCatcher() {
  const { say } = usePreferences();
  const rounds = useMemo(() => Array.from({ length: ROUNDS }, makeRound), []);
  const [index, setIndex] = useState(0);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [checked, setChecked] = useState(false);
  const [score, setScore] = useState(0);
  const [games, setGames] = useState(0);

  const round = rounds[index];

  useEffect(() => {
    if (round) void say(round.target);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, games]);

  if (!round) {
    return (
      <div className="stage stack">
        <h2>
          {score} of {ROUNDS} rounds perfect
        </h2>
        <button type="button" className="btn" onClick={() => {
          setIndex(0); setScore(0); setPicked(new Set()); setChecked(false); setGames((g) => g + 1);
        }}>
          <RotateCcw size={20} aria-hidden="true" /> Play again
        </button>
      </div>
    );
  }

  const rhymes = (word: string) => rimeOf(word) === rimeOf(round.target);

  function toggle(word: string) {
    if (checked) return;
    void say(word);
    setPicked((current) => {
      const next = new Set(current);
      if (next.has(word)) next.delete(word);
      else next.add(word);
      return next;
    });
  }

  function check() {
    setChecked(true);
    const perfect = round!.options.every((w) => rhymes(w) === picked.has(w));
    if (perfect) setScore((s) => s + 1);
  }

  return (
    <div className="stage stack">
      <p className="hint">
        Round {index + 1} of {ROUNDS}. Tap every word that rhymes with <strong>{round.target}</strong>.
      </p>
      <SpeakButton text={round.target} label={`Hear ${round.target}`} />
      <div className="choices">
        {round.options.map((word) => {
          let state = picked.has(word) ? " choice-picked" : "";
          if (checked) state = rhymes(word) ? " choice-right" : picked.has(word) ? " choice-wrong" : "";
          return (
            <button key={word} type="button" className={`choice-button${state}`} aria-pressed={picked.has(word)}
              onClick={() => toggle(word)}>
              {word}
            </button>
          );
        })}
      </div>
      {checked ? (
        <>
          <p className="note note-good">
            The rhyming words all end in -{rimeOf(round.target)}.
          </p>
          <button type="button" className="btn" onClick={() => {
            setIndex((i) => i + 1); setPicked(new Set()); setChecked(false);
          }}>
            Next round
          </button>
        </>
      ) : (
        <button type="button" className="btn" onClick={check} disabled={picked.size === 0}>
          Check
        </button>
      )}
    </div>
  );
}
