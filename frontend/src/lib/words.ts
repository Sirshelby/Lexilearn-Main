export interface Segment {
  text: string;
  isWord: boolean;
  start: number;
}

const WORD = /[A-Za-z]+(?:'[A-Za-z]+)?/g;

/** Split text into words and the bits between them, keeping character offsets. */
export function tokenize(text: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  for (const match of text.matchAll(WORD)) {
    const start = match.index ?? 0;
    if (start > last) segments.push({ text: text.slice(last, start), isWord: false, start: last });
    segments.push({ text: match[0], isWord: true, start });
    last = start + match[0].length;
  }
  if (last < text.length) segments.push({ text: text.slice(last), isWord: false, start: last });
  return segments;
}

/** True for letters shown on a vowel tile. y counts when it isn't the first letter. */
export function isVowelLetter(word: string, index: number): boolean {
  const ch = word[index]?.toLowerCase() ?? "";
  if ("aeiou".includes(ch)) return true;
  return ch === "y" && index > 0 && !"aeiou".includes(word[index - 1]?.toLowerCase() ?? "");
}

/** The rime: the last vowel group and everything after it (cat -> at, rain -> ain). */
export function rimeOf(word: string): string {
  const w = word.toLowerCase();
  const match = w.match(/[aeiouy]+[^aeiouy]*$/);
  return match ? match[0] : w;
}

export function shuffle<T>(items: readonly T[], random: () => number = Math.random): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [copy[i], copy[j]] = [copy[j] as T, copy[i] as T];
  }
  return copy;
}
