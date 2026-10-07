import { useQuery } from "@tanstack/react-query";
import { useLearner } from "../context/AuthContext";
import { api } from "./api";

export function useProgress() {
  const learner = useLearner();
  return useQuery({ queryKey: ["progress", learner.id], queryFn: () => api.progress(learner.id) });
}

export function useWordAnalysis(word: string | undefined) {
  return useQuery({
    queryKey: ["word", word],
    queryFn: () => api.analyzeWord(word!),
    enabled: Boolean(word),
    staleTime: Infinity,
  });
}

/** Same word all day, a different one tomorrow. */
export function wordOfTheDay(words: string[], date = new Date()): string | undefined {
  if (words.length === 0) return undefined;
  const start = new Date(date.getFullYear(), 0, 0);
  const day = Math.floor((date.getTime() - start.getTime()) / 86_400_000);
  return words[day % words.length];
}
