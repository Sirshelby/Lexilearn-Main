import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { api } from "../lib/api";
import { ErrorNote, Loading } from "./Feedback";
import { SpeakButton } from "./SpeakButton";
import { SyllableTiles } from "./Tiles";

/** Pop-up that breaks any word into syllables and reads it aloud. */
export function WordCard({ word, onClose }: { word: string; onClose: () => void }) {
  const learner = useLearner();
  const { say } = usePreferences();
  const dialog = useRef<HTMLDialogElement>(null);
  const clean = word.toLowerCase().replace(/[^a-z']/g, "");

  const { data, error, isPending } = useQuery({
    queryKey: ["word", clean],
    queryFn: () => api.analyzeWord(clean),
    staleTime: Infinity, // the analysis of a word never changes
  });

  useEffect(() => {
    const el = dialog.current;
    if (el && !el.open) el.showModal();
    void say(clean);
    // No cleanup: closing here would fire the dialog's close event during
    // React's dev-mode double mount and shut the card straight away.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clean]);

  return (
    <dialog
      ref={dialog}
      className="word-card"
      onClose={onClose}
      onClick={(e) => e.target === dialog.current && onClose()}
      aria-labelledby="word-card-title"
    >
      <div className="word-card-inner">
        <div className="word-card-head">
          <h2 id="word-card-title">{clean}</h2>
          <button type="button" className="btn-icon" onClick={onClose} aria-label="Close">
            <X size={22} />
          </button>
        </div>
        {isPending && <Loading />}
        {error && <ErrorNote error={error} />}
        {data && (
          <>
            <SyllableTiles syllables={data.syllables} size="lg" showLabels onSyllable={(s) => void say(s, { slow: true })} />
            <p className="word-card-facts">
              {data.syllables.length} syllable{data.syllables.length === 1 ? "" : "s"}
              {data.sound_count ? `, ${data.sound_count} sounds` : ""}.{" "}
              {data.required_level === null
                ? "This is a tricky word to learn by heart."
                : `You can sound it out from level ${data.required_level}.`}
            </p>
            <div className="row">
              <SpeakButton text={clean} />
              <SpeakButton text={clean} slow label="Slowly" />
            </div>
            <p className="hint">Tap a syllable to hear just that part. {learner.name}, try saying it with me.</p>
          </>
        )}
      </div>
    </dialog>
  );
}
