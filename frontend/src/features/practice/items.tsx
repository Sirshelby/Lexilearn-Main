import { Check } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { SpeakButton } from "../../components/SpeakButton";
import { LetterTiles } from "../../components/Tiles";
import { usePreferences } from "../../context/PreferencesContext";
import type { AnswerResult, PracticeItem } from "../../lib/types";

interface ItemProps {
  item: PracticeItem;
  onAnswer: (answer: string) => void;
  disabled: boolean;
  result: AnswerResult | null;
}

function HearButtons({ text }: { text: string }) {
  return (
    <div className="row">
      <SpeakButton text={text} label="Hear it again" />
      <SpeakButton text={text} label="Slowly" slow />
    </div>
  );
}

function useSayOnShow(text: string | null, key: number) {
  const { say } = usePreferences();
  useEffect(() => {
    if (text) void say(text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}

function Choices({ choices, onAnswer, disabled, result, asWords }: {
  choices: string[];
  onAnswer: (answer: string) => void;
  disabled: boolean;
  result: AnswerResult | null;
  asWords: boolean;
}) {
  const [picked, setPicked] = useState<string | null>(null);
  return (
    <div className={asWords ? "choices" : "choices choices-numbers"}>
      {choices.map((choice) => {
        let state = "";
        if (result && choice === result.expected) state = " choice-right";
        else if (result && choice === picked) state = " choice-wrong";
        return (
          <button
            key={choice}
            type="button"
            className={`choice-button${state}`}
            disabled={disabled}
            onClick={() => {
              setPicked(choice);
              onAnswer(choice);
            }}
          >
            {choice}
          </button>
        );
      })}
    </div>
  );
}

export function ListenChoose({ item, onAnswer, disabled, result }: ItemProps) {
  useSayOnShow(item.say, item.index);
  return (
    <>
      <HearButtons text={item.say ?? ""} />
      <Choices choices={item.choices ?? []} onAnswer={onAnswer} disabled={disabled} result={result} asWords />
    </>
  );
}

export function Spell({ item, onAnswer, disabled }: ItemProps) {
  useSayOnShow(item.say, item.index);
  const [value, setValue] = useState("");
  function submit(event: FormEvent) {
    event.preventDefault();
    if (value.trim()) onAnswer(value.trim());
  }
  return (
    <form onSubmit={submit} className="stack">
      <HearButtons text={item.say ?? ""} />
      <label className="visually-hidden" htmlFor={`spell-${item.index}`}>
        Type the word
      </label>
      <input
        id={`spell-${item.index}`}
        className="spell-input"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        autoComplete="off"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        disabled={disabled}
        autoFocus
      />
      <button type="submit" className="btn" disabled={disabled || !value.trim()}>
        <Check size={20} aria-hidden="true" /> Check my spelling
      </button>
    </form>
  );
}

export function CountSounds({ item, onAnswer, disabled, result }: ItemProps) {
  const word = item.word ?? "";
  return (
    <>
      <div className="stage-word">
        <LetterTiles word={word} size="lg" />
      </div>
      <div className="row">
        <SpeakButton text={word} />
        <SpeakButton text={word} label="Slowly" slow />
      </div>
      <Choices choices={item.choices ?? []} onAnswer={onAnswer} disabled={disabled} result={result} asWords={false} />
    </>
  );
}

/** Letters with tappable gaps between them. Tapping a gap adds or removes a split. */
export function SplitSyllables({ item, onAnswer, disabled }: ItemProps) {
  const word = item.word ?? "";
  const [splits, setSplits] = useState<Set<number>>(new Set());

  function toggle(position: number) {
    setSplits((current) => {
      const next = new Set(current);
      if (next.has(position)) next.delete(position);
      else next.add(position);
      return next;
    });
  }

  const answer = [...word].map((letter, i) => (splits.has(i) ? `-${letter}` : letter)).join("");

  return (
    <div className="stack">
      <div className="split-word" role="group" aria-label={`Split ${word}`}>
        {[...word].map((letter, i) => (
          <span key={i} className="split-unit">
            {i > 0 && (
              <button
                type="button"
                className={splits.has(i) ? "gap gap-on" : "gap"}
                onClick={() => toggle(i)}
                disabled={disabled}
                aria-pressed={splits.has(i)}
                aria-label={`Split before letter ${i + 1}, ${letter}`}
              />
            )}
            <LetterTiles word={letter} size="lg" offset={i} fullWord={word} />
          </span>
        ))}
      </div>
      <p className="hint">Your split: {answer}</p>
      <div className="row">
        <SpeakButton text={word} />
        <button type="button" className="btn" disabled={disabled || splits.size === 0} onClick={() => onAnswer(answer)}>
          <Check size={20} aria-hidden="true" /> Check
        </button>
      </div>
    </div>
  );
}

export function ItemView(props: ItemProps) {
  switch (props.item.kind) {
    case "listen_choose":
      return <ListenChoose {...props} />;
    case "spell":
      return <Spell {...props} />;
    case "count_sounds":
      return <CountSounds {...props} />;
    case "split_syllables":
      return <SplitSyllables {...props} />;
  }
}

export function SyllableChunks({ syllables }: { syllables: string[] }) {
  const word = syllables.join("");
  let offset = 0;
  return (
    <span className="syllables">
      {syllables.map((s, i) => {
        const start = offset;
        offset += s.length;
        return (
          <span key={i} className="syllable">
            <LetterTiles word={s} size="md" offset={start} fullWord={word} />
          </span>
        );
      })}
    </span>
  );
}
