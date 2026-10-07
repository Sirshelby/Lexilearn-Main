import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Mic, MicOff, Plus, Send, Trash2, Volume2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { ErrorNote, Loading } from "../components/Feedback";
import { TappableText } from "../components/TappableText";
import { useLearner } from "../context/AuthContext";
import { usePreferences } from "../context/PreferencesContext";
import { api } from "../lib/api";
import type { ChatMessage, ConversationDetail } from "../lib/types";
import { useSpeechRecognition } from "../lib/useSpeechRecognition";

const STARTERS = [
  'How do I read "rabbit"?',
  "Can you give me a sentence to practise?",
  "What does silent e do?",
  "Help me spell a word",
];

export function TutorPage() {
  const learner = useLearner();
  const queryClient = useQueryClient();
  const { say } = usePreferences();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const listKey = ["conversations", learner.id];
  const conversations = useQuery({ queryKey: listKey, queryFn: () => api.conversations(learner.id) });
  const detail = useQuery({
    queryKey: ["conversation", learner.id, activeId],
    queryFn: () => api.conversation(learner.id, activeId!),
    enabled: activeId !== null,
  });

  // Open the most recent chat when the page loads.
  useEffect(() => {
    if (activeId === null && conversations.data?.[0]) setActiveId(conversations.data[0].id);
  }, [activeId, conversations.data]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [detail.data?.messages.length, pending]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || pending) return;
    setError(null);
    setPending(content);
    setDraft("");
    try {
      let conversationId = activeId;
      if (!conversationId) {
        conversationId = (await api.createConversation(learner.id)).id;
        setActiveId(conversationId);
      }
      const { user_message, reply } = await api.sendMessage(learner.id, conversationId, content);
      queryClient.setQueryData<ConversationDetail>(["conversation", learner.id, conversationId], (old) =>
        old ? { ...old, messages: [...old.messages, user_message, reply] } : old,
      );
      void queryClient.invalidateQueries({ queryKey: ["conversation", learner.id, conversationId] });
      void queryClient.invalidateQueries({ queryKey: listKey });
    } catch (err) {
      setError(err);
      setDraft(content); // give them their message back
    } finally {
      setPending(null);
    }
  }

  const onSpoken = useCallback((text: string) => setDraft((d) => (d ? `${d} ${text}` : text)), []);
  const mic = useSpeechRecognition(onSpoken);

  async function remove(id: string) {
    await api.deleteConversation(learner.id, id);
    if (id === activeId) setActiveId(null);
    void queryClient.invalidateQueries({ queryKey: listKey });
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void send(draft);
    }
  }

  const messages: ChatMessage[] = activeId ? (detail.data?.messages ?? []) : [];

  return (
    <div className="page tutor">
      <aside className="chat-list" aria-label="Chats">
        <button type="button" className="btn btn-quiet" onClick={() => setActiveId(null)}>
          <Plus size={20} aria-hidden="true" /> New chat
        </button>
        {conversations.isPending && <Loading />}
        <ul>
          {conversations.data?.map((c) => (
            <li key={c.id} className={c.id === activeId ? "chat-item chat-item-active" : "chat-item"}>
              <button type="button" className="chat-open" onClick={() => setActiveId(c.id)}>
                {c.title}
              </button>
              <button type="button" className="btn-icon" onClick={() => void remove(c.id)}
                aria-label={`Delete chat: ${c.title}`}>
                <Trash2 size={18} />
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="chat" aria-label="Chat with Lexi">
        <div className="chat-thread" aria-live="polite">
          {messages.length === 0 && !pending && (
            <div className="chat-empty">
              <h1>Ask Lexi</h1>
              <p>
                Lexi helps with reading and spelling. Ask about any word and Lexi will break it down. You can tap
                any word Lexi writes to see it in tiles.
              </p>
              <div className="starter-list">
                {STARTERS.map((s) => (
                  <button key={s} type="button" className="starter" onClick={() => void send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {detail.isPending && activeId && <Loading />}

          {messages.map((m) =>
            m.role === "assistant" ? (
              <div key={m.id} className="bubble bubble-lexi">
                <TappableText text={m.content} />
                <button type="button" className="btn-text" onClick={() => void say(m.content)}>
                  <Volume2 size={18} aria-hidden="true" /> Read aloud
                </button>
              </div>
            ) : (
              <div key={m.id} className="bubble bubble-me">
                <p>{m.content}</p>
              </div>
            ),
          )}

          {pending && (
            <>
              <div className="bubble bubble-me">
                <p>{pending}</p>
              </div>
              <div className="bubble bubble-lexi">
                <Loading label="Lexi is thinking" />
              </div>
            </>
          )}
          <div ref={endRef} />
        </div>

        {error !== null && <ErrorNote error={error} />}

        <form
          className="composer"
          onSubmit={(e: FormEvent) => {
            e.preventDefault();
            void send(draft);
          }}
        >
          <label htmlFor="message" className="visually-hidden">
            Message to Lexi
          </label>
          <textarea
            id="message"
            rows={2}
            value={draft}
            maxLength={1000}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type a question, or tap the microphone"
          />
          {mic.supported && (
            <button
              type="button"
              className={mic.listening ? "btn-icon btn-icon-live" : "btn-icon"}
              onClick={mic.listening ? mic.stop : mic.start}
              aria-label={mic.listening ? "Stop listening" : "Speak your question"}
              aria-pressed={mic.listening}
            >
              {mic.listening ? <MicOff size={22} /> : <Mic size={22} />}
            </button>
          )}
          <button type="submit" className="btn" disabled={!draft.trim() || pending !== null}>
            <Send size={20} aria-hidden="true" /> Send
          </button>
        </form>
      </section>
    </div>
  );
}
