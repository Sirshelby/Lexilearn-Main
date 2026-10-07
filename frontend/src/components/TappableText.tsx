import { useState } from "react";
import { tokenize } from "../lib/words";
import { WordCard } from "./WordCard";

/**
 * Renders text where every word can be tapped to open a word card.
 * `highlightAt` is a character offset used by read-along mode.
 */
export function TappableText({ text, highlightAt, className }: {
  text: string;
  highlightAt?: number | null;
  className?: string;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const segments = tokenize(text);

  return (
    <>
      <p className={className}>
        {segments.map((seg, i) =>
          seg.isWord ? (
            <button
              key={i}
              type="button"
              className={
                highlightAt != null && highlightAt >= seg.start && highlightAt < seg.start + seg.text.length
                  ? "word word-current"
                  : "word"
              }
              onClick={() => setOpen(seg.text)}
            >
              {seg.text}
            </button>
          ) : (
            <span key={i}>{seg.text}</span>
          ),
        )}
      </p>
      {open && <WordCard word={open} onClose={() => setOpen(null)} />}
    </>
  );
}
