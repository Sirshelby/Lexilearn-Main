import type { Syllable, SyllableType } from "../lib/types";
import { isVowelLetter } from "../lib/words";

type Size = "sm" | "md" | "lg";

export const SYLLABLE_LABELS: Record<SyllableType, string> = {
  closed: "Closed",
  open: "Open",
  vce: "Silent e",
  vowel_team: "Vowel team",
  r_controlled: "Bossy r",
  consonant_le: "Consonant-le",
  irregular: "Tricky",
};

/** One letter tile per letter. Vowels sit on salmon tiles like OG letter cards. */
export function LetterTiles({ word, size = "md", offset = 0, fullWord }: {
  word: string;
  size?: Size;
  offset?: number; // position of this chunk inside fullWord, for the y rule
  fullWord?: string;
}) {
  const context = fullWord ?? word;
  return (
    <span className={`tiles tiles-${size}`} aria-hidden="true">
      {[...word].map((letter, i) => (
        <span key={i} className={isVowelLetter(context, offset + i) ? "tile tile-vowel" : "tile"}>
          {letter}
        </span>
      ))}
    </span>
  );
}

export function SyllableTiles({
  syllables,
  size = "md",
  showLabels = false,
  onSyllable,
}: {
  syllables: Syllable[];
  size?: Size;
  showLabels?: boolean;
  onSyllable?: (text: string) => void;
}) {
  const word = syllables.map((s) => s.text).join("");
  let offset = 0;
  return (
    <span className="syllables" aria-label={`${word}: ${syllables.map((s) => s.text).join(", ")}`}>
      {syllables.map((s, i) => {
        const start = offset;
        offset += s.text.length;
        const content = (
          <>
            <LetterTiles word={s.text} size={size} offset={start} fullWord={word} />
            <span className="syllable-bar" style={{ background: `var(--syl-${s.type})` }} />
            {showLabels && <span className="syllable-label">{SYLLABLE_LABELS[s.type]}</span>}
          </>
        );
        return onSyllable ? (
          <button
            key={i}
            type="button"
            className="syllable syllable-button"
            onClick={() => onSyllable(s.text)}
            aria-label={`Hear ${s.text}`}
          >
            {content}
          </button>
        ) : (
          <span key={i} className="syllable">
            {content}
          </span>
        );
      })}
    </span>
  );
}

export function SyllableLegend() {
  const shown: SyllableType[] = ["closed", "open", "vce", "vowel_team", "r_controlled", "consonant_le"];
  return (
    <ul className="legend">
      {shown.map((type) => (
        <li key={type}>
          <span className="legend-swatch" style={{ background: `var(--syl-${type})` }} />
          {SYLLABLE_LABELS[type]}
        </li>
      ))}
    </ul>
  );
}
