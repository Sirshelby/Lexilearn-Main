import { Puzzle, Sparkles } from "lucide-react";
import { useState } from "react";
import { RhymeCatcher } from "../features/games/RhymeCatcher";
import { SyllableBuilder } from "../features/games/SyllableBuilder";
import { useProgress } from "../lib/useProgress";

type Game = "builder" | "rhymes";

export function GamesPage() {
  const [game, setGame] = useState<Game | null>(null);
  const progress = useProgress();

  return (
    <div className="page">
      <h1>Games</h1>
      <div className="game-picker" role="group" aria-label="Choose a game">
        <button type="button" className={game === "builder" ? "game-option game-option-on" : "game-option"}
          onClick={() => setGame("builder")} aria-pressed={game === "builder"}>
          <Puzzle size={28} aria-hidden="true" />
          <span>
            <strong>Syllable builder</strong>
            <span className="hint">Hear a word and put its parts in order.</span>
          </span>
        </button>
        <button type="button" className={game === "rhymes" ? "game-option game-option-on" : "game-option"}
          onClick={() => setGame("rhymes")} aria-pressed={game === "rhymes"}>
          <Sparkles size={28} aria-hidden="true" />
          <span>
            <strong>Rhyme catcher</strong>
            <span className="hint">Find the words that sound the same at the end.</span>
          </span>
        </button>
      </div>
      {game === "builder" && <SyllableBuilder maxLevel={progress.data?.current_level ?? 1} />}
      {game === "rhymes" && <RhymeCatcher />}
    </div>
  );
}
