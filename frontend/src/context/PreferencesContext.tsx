import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { speak, type SpeakOptions } from "../lib/speech";
import type { ReadingPreferences } from "../lib/types";
import { useAuth } from "./AuthContext";

export const DEFAULT_PREFERENCES: ReadingPreferences = {
  font: "lexend",
  text_size: 20,
  letter_spacing: "wide",
  line_spacing: "relaxed",
  theme: "soft",
  overlay: "none",
  speech_rate: 0.9,
  premium_voice: true,
  show_syllable_colours: true,
};

const TRACKING = { normal: "0.01em", wide: "0.05em", wider: "0.1em" } as const;
const LEADING = { normal: "1.5", relaxed: "1.7", loose: "1.95" } as const;

interface PreferencesState {
  prefs: ReadingPreferences;
  update: (changes: Partial<ReadingPreferences>) => void;
  saving: boolean;
  say: (text: string, options?: Partial<SpeakOptions>) => Promise<void>;
}

const PreferencesContext = createContext<PreferencesState | null>(null);

function apply(prefs: ReadingPreferences) {
  const root = document.documentElement;
  root.dataset.theme = prefs.theme;
  root.dataset.font = prefs.font;
  root.dataset.syllableColours = prefs.show_syllable_colours ? "on" : "off";
  root.style.setProperty("--text-size", `${prefs.text_size}px`);
  root.style.setProperty("--tracking", TRACKING[prefs.letter_spacing]);
  root.style.setProperty("--leading", LEADING[prefs.line_spacing]);
}

export function PreferencesProvider({ children }: { children: ReactNode }) {
  const { learner, replaceLearner } = useAuth();
  const [prefs, setPrefs] = useState<ReadingPreferences>(DEFAULT_PREFERENCES);
  const [saving, setSaving] = useState(false);
  const saveTimer = useRef<number | undefined>(undefined);

  const prefsRef = useRef(prefs);

  // Switching learner switches the whole look of the app to their settings.
  // Only the id is a dependency on purpose: re-syncing after every save would
  // overwrite changes the learner made while the save was in flight.
  useEffect(() => {
    const next = { ...DEFAULT_PREFERENCES, ...(learner?.preferences ?? {}) };
    prefsRef.current = next;
    setPrefs(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [learner?.id]);

  useEffect(() => apply(prefs), [prefs]);

  const update = useCallback(
    (changes: Partial<ReadingPreferences>) => {
      const next = { ...prefsRef.current, ...changes };
      prefsRef.current = next;
      setPrefs(next);
      if (!learner) return;
      // Apply instantly, save once the learner stops fiddling with sliders.
      window.clearTimeout(saveTimer.current);
      saveTimer.current = window.setTimeout(async () => {
        setSaving(true);
        try {
          replaceLearner(await api.updateLearner(learner.id, { preferences: next }));
        } finally {
          setSaving(false);
        }
      }, 600);
    },
    [learner, replaceLearner],
  );

  const say = useCallback(
    (text: string, options: Partial<SpeakOptions> = {}) =>
      speak(text, { rate: prefs.speech_rate, premium: prefs.premium_voice, ...options }),
    [prefs.speech_rate, prefs.premium_voice],
  );

  const value = useMemo(() => ({ prefs, update, saving, say }), [prefs, update, saving, say]);
  return (
    <PreferencesContext.Provider value={value}>
      {children}
      <div className="overlay" data-colour={prefs.overlay} aria-hidden="true" />
    </PreferencesContext.Provider>
  );
}

export function usePreferences(): PreferencesState {
  const ctx = useContext(PreferencesContext);
  if (!ctx) throw new Error("usePreferences must be used inside PreferencesProvider");
  return ctx;
}
