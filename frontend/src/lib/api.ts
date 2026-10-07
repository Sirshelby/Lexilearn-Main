import type {
  AnswerResult,
  AuthResponse,
  ChatMessage,
  CompleteResult,
  Conversation,
  ConversationDetail,
  Curriculum,
  Learner,
  Passage,
  PracticeSession,
  ProgressSummary,
  ReadingPreferences,
  TextCheck,
  User,
  WordAnalysis,
} from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// The access token only ever lives in memory. The refresh token is an
// httpOnly cookie the browser sends to /api/v1/auth/*, so JavaScript (and any
// injected script) can't read it.
let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onSessionExpired: () => void = () => {};

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler;
}

async function refreshAccessToken(): Promise<boolean> {
  // Several requests can fail at once when the token expires; make sure
  // they all wait for the same refresh instead of racing each other.
  refreshing ??= fetch(`${BASE}/auth/refresh`, { method: "POST", credentials: "include" })
    .then(async (res) => {
      if (!res.ok) return false;
      const body = (await res.json()) as { access_token: string };
      accessToken = body.access_token;
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function errorMessage(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail) && body.detail[0]?.msg) return body.detail[0].msg;
  } catch {
    // not JSON
  }
  return `Request failed (${res.status})`;
}

async function request(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const res = await fetch(`${BASE}${path}`, { ...init, headers, credentials: "include" });

  if (res.status === 401 && retry && !path.startsWith("/auth/")) {
    if (await refreshAccessToken()) return request(path, init, false);
    onSessionExpired();
  }
  if (!res.ok) throw new ApiError(res.status, await errorMessage(res));
  return res;
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await request(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const post = <T>(path: string, body?: unknown) =>
  json<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const patch = <T>(path: string, body: unknown) =>
  json<T>(path, { method: "PATCH", body: JSON.stringify(body) });
const del = (path: string) => json<void>(path, { method: "DELETE" });

const learnerPath = (learnerId: string) => `/learners/${learnerId}`;

export const api = {
  // auth
  register: (body: {
    email: string;
    password: string;
    display_name: string;
    account_type: User["account_type"];
    learner_name?: string;
    learner_age_band?: string;
    timezone: string;
  }) => post<AuthResponse>("/auth/register", body),
  login: (email: string, password: string) => post<AuthResponse>("/auth/login", { email, password }),
  logout: () => post<void>("/auth/logout"),
  me: () => json<User>("/auth/me"),
  restoreSession: refreshAccessToken,

  // learners
  createLearner: (body: { name: string; age_band?: string | null; timezone: string }) =>
    post<Learner>("/learners", body),
  updateLearner: (id: string, body: { name?: string; age_band?: string | null; preferences?: ReadingPreferences }) =>
    patch<Learner>(learnerPath(id), body),
  deleteLearner: (id: string) => del(learnerPath(id)),

  // literacy
  curriculum: () => json<Curriculum>("/curriculum"),
  analyzeWord: (word: string, level?: number) => post<WordAnalysis>("/literacy/analyze-word", { word, level }),
  checkText: (text: string, level: number) => post<TextCheck>("/literacy/check-text", { text, level }),

  // progress & practice
  progress: (learnerId: string) => json<ProgressSummary>(`${learnerPath(learnerId)}/progress`),
  startPractice: (learnerId: string, skillCode?: string) =>
    post<PracticeSession>(`${learnerPath(learnerId)}/practice/sessions`, skillCode ? { skill_code: skillCode } : {}),
  answer: (learnerId: string, sessionId: string, itemIndex: number, answer: string) =>
    post<AnswerResult>(`${learnerPath(learnerId)}/practice/sessions/${sessionId}/answers`, {
      item_index: itemIndex,
      answer,
    }),
  completePractice: (learnerId: string, sessionId: string) =>
    post<CompleteResult>(`${learnerPath(learnerId)}/practice/sessions/${sessionId}/complete`),

  // tutor
  conversations: (learnerId: string) => json<Conversation[]>(`${learnerPath(learnerId)}/tutor/conversations`),
  createConversation: (learnerId: string) => post<Conversation>(`${learnerPath(learnerId)}/tutor/conversations`),
  conversation: (learnerId: string, id: string) =>
    json<ConversationDetail>(`${learnerPath(learnerId)}/tutor/conversations/${id}`),
  deleteConversation: (learnerId: string, id: string) =>
    del(`${learnerPath(learnerId)}/tutor/conversations/${id}`),
  sendMessage: (learnerId: string, id: string, content: string) =>
    post<{ user_message: ChatMessage; reply: ChatMessage }>(
      `${learnerPath(learnerId)}/tutor/conversations/${id}/messages`,
      { content },
    ),

  // reading
  passage: (learnerId: string, topic?: string, level?: number) =>
    post<Passage>(`${learnerPath(learnerId)}/reading/passage`, { topic: topic || null, level: level ?? null }),

  // speech: returns null when the server has no premium voice, so the
  // caller can fall back to the browser's own speech synthesis.
  tts: async (text: string, slow: boolean): Promise<Blob | null> => {
    try {
      const res = await request("/speech/tts", { method: "POST", body: JSON.stringify({ text, slow }) });
      return await res.blob();
    } catch (err) {
      if (err instanceof ApiError && (err.status === 503 || err.status === 429)) return null;
      throw err;
    }
  },
};
