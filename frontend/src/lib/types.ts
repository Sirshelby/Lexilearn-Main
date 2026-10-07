// These mirror the Pydantic schemas in backend/app/schemas. If the API
// grows much more, generating them from /openapi.json would be the next step.

export type Font = "lexend" | "atkinson" | "opendyslexic" | "system";
export type Theme = "soft" | "cream" | "dark" | "high_contrast";
export type Overlay = "none" | "blue" | "yellow" | "green" | "rose" | "peach";

export interface ReadingPreferences {
  font: Font;
  text_size: number;
  letter_spacing: "normal" | "wide" | "wider";
  line_spacing: "normal" | "relaxed" | "loose";
  theme: Theme;
  overlay: Overlay;
  speech_rate: number;
  premium_voice: boolean;
  show_syllable_colours: boolean;
}

export interface Learner {
  id: string;
  name: string;
  age_band: string | null;
  timezone: string;
  preferences: ReadingPreferences;
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  account_type: "parent" | "teacher" | "learner";
  learners: Learner[];
}

export interface AuthResponse {
  access_token: string;
  expires_in: number;
  user: User;
}

export interface Syllable {
  text: string;
  type: SyllableType;
}

export type SyllableType =
  | "closed"
  | "open"
  | "vce"
  | "vowel_team"
  | "r_controlled"
  | "consonant_le"
  | "irregular";

export interface WordAnalysis {
  word: string;
  syllables: Syllable[];
  patterns: string[];
  required_level: number | null;
  heart_word_level: number | null;
  sound_count: number | null;
  decodable: boolean | null;
}

export interface TextCheck {
  level: number;
  score: number;
  band: "independent" | "with_support" | "too_hard";
  total_words: number;
  decodable_words: number;
  tricky_words: string[];
  words: { word: string; decodable: boolean; required_level: number | null; is_heart_word: boolean }[];
}

export interface Skill {
  code: string;
  level: number;
  title: string;
  focus: string;
  tip: string;
  words: string[];
}

export interface Curriculum {
  levels: { level: number; title: string; skills: Skill[] }[];
}

export type SkillStatus = "locked" | "available" | "in_progress" | "mastered";

export interface ProgressSummary {
  current_skill: Skill | null;
  current_level: number;
  level_title: string;
  skills_mastered: number;
  total_skills: number;
  streak_days: number;
  minutes_this_week: number;
  sessions_this_week: number;
  recent: { skill_code: string; skill_title: string; accuracy: number; completed_at: string }[];
  recommendations: string[];
  skills: {
    code: string;
    level: number;
    title: string;
    status: SkillStatus;
    sessions: number;
    accuracy: number | null;
  }[];
}

export type ItemKind = "listen_choose" | "spell" | "count_sounds" | "split_syllables";

export interface PracticeItem {
  index: number;
  kind: ItemKind;
  prompt: string;
  say: string | null;
  word: string | null;
  choices: string[] | null;
}

export interface PracticeSession {
  id: string;
  skill_code: string;
  skill_title: string;
  tip: string;
  items: PracticeItem[];
}

export interface AnswerResult {
  correct: boolean;
  expected: string;
  feedback: string;
  syllables: string[] | null;
}

export interface CompleteResult {
  skill_code: string;
  correct: number;
  total: number;
  accuracy: number;
  mastered_now: boolean;
  skill_status: string;
  next_skill_code: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[];
}

export interface Passage {
  title: string;
  text: string;
  level: number;
  score: number;
  source: "generated" | "library";
  tricky_words: string[];
}
