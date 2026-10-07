import { api } from "./api";

// Premium (ElevenLabs) audio when the server has it, otherwise the browser's
// built-in voices. Clips are cached as object URLs because practice repeats
// the same words over and over.
const clipCache = new Map<string, string>();
let premiumAvailable = true;
let premiumChecked: Promise<void> | null = null;
let currentAudio: HTMLAudioElement | null = null;

function checkPremium(): Promise<void> {
  premiumChecked ??= fetch("/api/v1/health")
    .then((res) => res.json())
    .then((body: { speech?: string }) => {
      premiumAvailable = body.speech === "premium";
    })
    .catch(() => {});
  return premiumChecked;
}

export interface SpeakOptions {
  rate: number;
  premium: boolean;
  slow?: boolean;
}

export function stopSpeaking() {
  currentAudio?.pause();
  currentAudio = null;
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

function pickVoice(): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices();
  return (
    voices.find((v) => v.lang.startsWith("en") && /natural|neural|google/i.test(v.name)) ??
    voices.find((v) => v.lang.startsWith("en"))
  );
}

export function browserUtterance(text: string, rate: number): SpeechSynthesisUtterance {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = rate;
  utterance.lang = "en";
  const voice = pickVoice();
  if (voice) utterance.voice = voice;
  return utterance;
}

export async function speak(text: string, { rate, premium, slow = false }: SpeakOptions): Promise<void> {
  stopSpeaking();
  const clean = text.trim();
  if (!clean) return;

  if (premium) await checkPremium();
  if (premium && premiumAvailable) {
    const key = `${slow}|${clean}`;
    try {
      let url = clipCache.get(key);
      if (!url) {
        const blob = await api.tts(clean, slow);
        if (blob) {
          url = URL.createObjectURL(blob);
          clipCache.set(key, url);
        } else {
          premiumAvailable = false; // server said no; stop asking this session
        }
      }
      if (url) {
        currentAudio = new Audio(url);
        await currentAudio.play();
        return;
      }
    } catch {
      // network hiccup or autoplay block: fall through to the browser voice
    }
  }

  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.speak(browserUtterance(clean, slow ? rate * 0.7 : rate));
}

/**
 * Read a passage aloud and report which character is being spoken, for
 * word-by-word highlighting. Browser voices only, since we can't get word
 * timings back from the audio files.
 */
export function readAlong(
  text: string,
  rate: number,
  onWord: (charIndex: number) => void,
  onEnd: () => void,
): () => void {
  stopSpeaking();
  if (!("speechSynthesis" in window)) {
    onEnd();
    return () => {};
  }
  const utterance = browserUtterance(text, rate);
  utterance.onboundary = (event) => {
    if (event.name === "word") onWord(event.charIndex);
  };
  utterance.onend = onEnd;
  utterance.onerror = onEnd;
  window.speechSynthesis.speak(utterance);
  return () => {
    utterance.onend = null;
    window.speechSynthesis.cancel();
    onEnd();
  };
}
