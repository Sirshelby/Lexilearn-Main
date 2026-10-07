import { describe, expect, it } from "vitest";
import { isVowelLetter, rimeOf, shuffle, tokenize } from "./words";

describe("tokenize", () => {
  it("keeps punctuation and offsets so read-along can highlight the right word", () => {
    const segments = tokenize("Sam's cat sat.");
    expect(segments.filter((s) => s.isWord).map((s) => s.text)).toEqual(["Sam's", "cat", "sat"]);
    expect(segments.map((s) => s.text).join("")).toBe("Sam's cat sat.");
    expect(segments[2]).toEqual({ text: "cat", isWord: true, start: 6 });
  });
});

describe("isVowelLetter", () => {
  it("treats y as a vowel only after a consonant", () => {
    expect(isVowelLetter("yes", 0)).toBe(false);
    expect(isVowelLetter("my", 1)).toBe(true);
    expect(isVowelLetter("cat", 1)).toBe(true);
  });
});

describe("rimeOf", () => {
  it("finds the rhyming part", () => {
    expect(rimeOf("cat")).toBe("at");
    expect(rimeOf("ship")).toBe("ip");
    expect(rimeOf("rain")).toBe("ain");
  });
});

describe("shuffle", () => {
  it("keeps every item", () => {
    expect(shuffle([1, 2, 3, 4]).sort()).toEqual([1, 2, 3, 4]);
  });
});
