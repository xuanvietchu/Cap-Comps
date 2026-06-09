"use client";

import { useEffect, useMemo, useState } from "react";

import ChatSidebar from "./ChatSidebar";
import HouseDetailsForm from "./HouseDetailsForm";
import { HouseDetails } from "./houseDetails";

type PredictionBand = {
  predicted_price: number;
  predicted_price_low: number;
  predicted_price_high: number;
  confidence_level: "high" | "medium" | "low" | string;
  interval_width: number;
  interval_width_ratio: number;
};

type Comp = {
  address: string;
  sold_price: number;
  sold_date: string;
  distance_km?: number | null;
  similarity_score: number;
  leaf_similarity_score?: number | null;
  price_per_sqft_similarity?: number | null;
  leaf_matches?: number | null;
  leaf_count?: number | null;
  subject_price_per_sqft?: number | null;
  candidate_price_per_sqft?: number | null;
  predicted_value?: number | null;
  yearBuilt?: number | null;
};

type ExplanationFeature = {
  feature: string;
  value: string;
  shap_log_effect: number;
  approx_pct_effect: number;
  direction: "up" | "down" | "neutral";
};

type ExplanationSection = {
  kind: string;
  summary?: string;
  predicted_price?: number | null;
  top_positive?: ExplanationFeature[];
  top_negative?: ExplanationFeature[];
  feature_count?: number;
  top_comp?: Comp | null;
  top_comp_count?: number;
  top_comps?: Comp[];
};

type ExplanationPayload = {
  price?: ExplanationSection | null;
  comps?: ExplanationSection | null;
};

type IntentAnalysis = {
  intent?: string;
  confidence?: string;
  summary?: string;
  planned_tools?: string[];
};

type DisplayOptions = {
  show_prediction?: boolean;
  show_comps?: boolean;
};

type AgentTraceEvent = {
  step: string;
  detail: string;
  payload?: unknown;
};

type Message = {
  id: string;
  role: "user" | "agent";
  content: string;
  comps?: Comp[];
  prediction?: PredictionBand | null;
  confidence_level?: string;
  intent?: string;
  explanation?: ExplanationPayload | null;
  display?: DisplayOptions;
  intent_analysis?: IntentAnalysis | null;
  agent_trace?: AgentTraceEvent[];
  isStreaming?: boolean;
};

type Conversation = {
  id: string;
  title: string;
  houseDetails: HouseDetails;
  messages: Message[];
};

const STORAGE_KEY = "kv-housing-comps-conversations";
const HISTORY_MESSAGE_LIMIT = 16;

function createId() {
  return crypto.randomUUID();
}

function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function formatPercent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatPerSqft(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }

  return `${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value)}/sqft`;
}

function honestDoorUrl(address: string) {
  const slug = address.trim().toLowerCase().replace(/\s+/g, "-");
  return `https://www.honestdoor.com/property/${encodeURIComponent(
    `${slug}-edmonton-ab`,
  )}`;
}

function normalizeMessage(
  message: Partial<Message>,
  fallbackRole: "user" | "agent",
): Message {
  return {
    id: message.id || createId(),
    role: message.role ?? fallbackRole,
    content: message.content ?? "",
    comps: message.comps ?? [],
    prediction: message.prediction ?? null,
    confidence_level: message.confidence_level,
    intent: message.intent,
    explanation: message.explanation ?? null,
    display: {
      show_prediction: message.display?.show_prediction ?? false,
      show_comps: message.display?.show_comps ?? false,
    },
    intent_analysis: message.intent_analysis ?? null,
    agent_trace: message.agent_trace ?? [],
    isStreaming: message.isStreaming ?? false,
  };
}

function normalizeConversation(raw: Partial<Conversation>): Conversation {
  return {
    id: raw.id || createId(),
    title: raw.title || "New comps search",
    houseDetails: raw.houseDetails as HouseDetails,
    messages: (raw.messages || []).map((message) =>
      normalizeMessage(message, message.role === "user" ? "user" : "agent"),
    ),
  };
}

function loadStoredConversations() {
  if (typeof window === "undefined") {
    return [];
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed = JSON.parse(raw) as Partial<Conversation>[];
    if (!Array.isArray(parsed)) return [];

    return parsed.map(normalizeConversation);
  } catch {
    return [];
  }
}

function buildConversationHistory(messages: Message[]) {
  return messages
    .filter((message) => !message.isStreaming && message.content.trim())
    .slice(-HISTORY_MESSAGE_LIMIT)
    .map((message) => ({
      role: message.role === "agent" ? "assistant" : message.role,
      content: message.content,
    }));
}

export default function AgentChat() {
  const [conversations, setConversations] = useState<Conversation[]>(() =>
    loadStoredConversations(),
  );
  const [activeId, setActiveId] = useState<string | null>(
    () => loadStoredConversations()[0]?.id ?? null,
  );
  const [showForm, setShowForm] = useState(false);
  const [editingConversationId, setEditingConversationId] = useState<
    string | null
  >(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [openCompsByMessageId, setOpenCompsByMessageId] = useState<
    Record<string, boolean>
  >({});
  const [openAgentTraceByMessageId, setOpenAgentTraceByMessageId] = useState<
    Record<string, boolean>
  >({});

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    } catch {
      // Ignore storage quota and private mode issues.
    }
  }, [conversations]);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [activeId, conversations],
  );

  function handleNewChat() {
    setActiveId(null);
    setShowForm(true);
    setEditingConversationId(null);
  }

  function handleDeleteChat(id: string) {
    const conversation = conversations.find((item) => item.id === id);
    if (!conversation) return;

    const shouldDelete = window.confirm(`Delete chat "${conversation.title}"?`);
    if (!shouldDelete) return;

    setConversations((prev) => prev.filter((item) => item.id !== id));
    setOpenCompsByMessageId((prev) => {
      const next = { ...prev };
      conversation.messages.forEach((message) => {
        delete next[message.id];
      });
      return next;
    });
    setOpenAgentTraceByMessageId((prev) => {
      const next = { ...prev };
      conversation.messages.forEach((message) => {
        delete next[message.id];
      });
      return next;
    });

    if (activeId === id) {
      const remaining = conversations.filter((item) => item.id !== id);
      setActiveId(remaining[0]?.id ?? null);
    }

    if (editingConversationId === id) {
      setEditingConversationId(null);
      setShowForm(false);
    }
  }

  function handleCreateChat(houseDetails: HouseDetails) {
    const id = createId();

    const newConversation: Conversation = {
      id,
      title: houseDetails.address || "New comps search",
      houseDetails,
      messages: [
        normalizeMessage(
          {
            role: "agent",
            content:
              "House details saved. Ask me for price, comps, or an explanation.",
          },
          "agent",
        ),
      ],
    };

    setConversations((prev) => [newConversation, ...prev]);
    setActiveId(id);
    setShowForm(false);
  }

  function handleSaveHouseDetails(details: HouseDetails) {
    if (editingConversationId) {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === editingConversationId
            ? {
                ...conv,
                title: details.address || conv.title,
                houseDetails: details,
              }
            : conv,
        ),
      );

      setShowForm(false);
      setEditingConversationId(null);
      return;
    }

    handleCreateChat(details);
  }

  function toggleComps(messageId: string) {
    setOpenCompsByMessageId((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  }

  function toggleAgentTrace(messageId: string) {
    setOpenAgentTraceByMessageId((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  }

  async function sendMessage() {
    if (!input.trim() || !activeConversation) return;

    const messageToSend = input.trim();
    const userMessage = normalizeMessage(
      {
        id: createId(),
        role: "user",
        content: messageToSend,
      },
      "user",
    );
    const pendingAgentMessage = normalizeMessage(
      {
        id: createId(),
        role: "agent",
        content: "Analyzing intent and choosing tools...",
        agent_trace: [],
        isStreaming: true,
      },
      "agent",
    );

    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversation.id
          ? {
              ...conv,
              messages: [...conv.messages, userMessage, pendingAgentMessage],
            }
          : conv,
      ),
    );

    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageToSend,
          house_details: activeConversation.houseDetails,
          conversation_id: activeConversation.id,
          conversation_history: buildConversationHistory(
            activeConversation.messages,
          ),
        }),
      });

      if (!res.ok) {
        throw new Error(`Backend returned ${res.status}`);
      }

      if (!res.body) {
        throw new Error("Backend response did not include a stream");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);

          if (event.type === "trace") {
            const traceEvent = event.event as AgentTraceEvent;
            setOpenAgentTraceByMessageId((prev) => ({
              ...prev,
              [pendingAgentMessage.id]: true,
            }));
            setConversations((prev) =>
              prev.map((conv) =>
                conv.id === activeConversation.id
                  ? {
                      ...conv,
                      messages: conv.messages.map((message) =>
                        message.id === pendingAgentMessage.id
                          ? {
                              ...message,
                              content: traceEvent.detail,
                              agent_trace: [
                                ...(message.agent_trace ?? []),
                                traceEvent,
                              ],
                              intent_analysis:
                                traceEvent.step === "intent"
                                  ? (traceEvent.payload as IntentAnalysis)
                                  : message.intent_analysis,
                              intent:
                                traceEvent.step === "intent" &&
                                typeof (traceEvent.payload as IntentAnalysis)
                                  ?.intent === "string"
                                  ? (traceEvent.payload as IntentAnalysis)
                                      .intent
                                  : message.intent,
                            }
                          : message,
                      ),
                    }
                  : conv,
              ),
            );
          }

          if (event.type === "final") {
            const data = event.response;
            const display = data.display ?? {
              show_prediction: false,
              show_comps: false,
            };
            setConversations((prev) =>
              prev.map((conv) =>
                conv.id === activeConversation.id
                  ? {
                      ...conv,
                      messages: conv.messages.map((message) =>
                        message.id === pendingAgentMessage.id
                          ? normalizeMessage(
                              {
                                ...message,
                                content: data.answer ?? "I found some results.",
                                comps: display.show_comps
                                  ? (data.comps ?? [])
                                  : [],
                                prediction: display.show_prediction
                                  ? (data.prediction ?? null)
                                  : null,
                                confidence_level: data.confidence_level,
                                intent: data.intent,
                                explanation: data.explanation ?? null,
                                display,
                                intent_analysis:
                                  data.intent_analysis ??
                                  message.intent_analysis ??
                                  null,
                                agent_trace:
                                  data.agent_trace ?? message.agent_trace ?? [],
                                isStreaming: false,
                              },
                              "agent",
                            )
                          : message,
                      ),
                    }
                  : conv,
              ),
            );

            if (display.show_comps && (data.comps?.length ?? 0) > 0) {
              setOpenCompsByMessageId((prev) => ({
                ...prev,
                [pendingAgentMessage.id]: true,
              }));
            }
          }

          if (event.type === "error") {
            throw new Error(event.message ?? "Backend stream failed");
          }
        }
      }
    } catch {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === activeConversation.id
            ? {
                ...conv,
                messages: conv.messages.map((message) =>
                  message.id === pendingAgentMessage.id
                    ? normalizeMessage(
                        {
                          ...message,
                          content:
                            "I could not reach the backend. Make sure FastAPI is running on http://localhost:8000.",
                          isStreaming: false,
                        },
                        "agent",
                      )
                    : message,
                ),
              }
            : conv,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full w-full overflow-hidden border border-white/10 bg-[#0b1120]/95 shadow-[0_24px_80px_rgba(0,0,0,0.45)]">
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onNewChat={handleNewChat}
        onSelectChat={(id) => {
          setActiveId(id);
          setShowForm(false);
        }}
        onDeleteChat={handleDeleteChat}
      />

      <section className="flex min-w-0 flex-1 min-h-0 flex-col bg-[#0b1120]">
        {showForm ? (
          <HouseDetailsForm
            initialDetails={
              editingConversationId
                ? conversations.find((c) => c.id === editingConversationId)
                    ?.houseDetails
                : undefined
            }
            onSubmit={handleSaveHouseDetails}
            onCancel={() => {
              setShowForm(false);
              setEditingConversationId(null);
            }}
          />
        ) : activeConversation ? (
          <>
            <div className="border-b border-white/10 px-4 py-4 sm:px-6">
              <div className="mx-auto flex w-full max-w-3xl items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
                    Housing Comps Agent
                  </p>
                  <h2 className="mt-2 text-xl font-semibold text-white">
                    {activeConversation.title}
                  </h2>
                  <p className="mt-1 text-sm text-slate-400">
                    {activeConversation.houseDetails.bedroomsCount} bed /{" "}
                    {activeConversation.houseDetails.bathroomsCount} bath /{" "}
                    {activeConversation.houseDetails.livingArea} sqft
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      setEditingConversationId(activeConversation.id);
                      setShowForm(true);
                    }}
                    className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
                  >
                    Edit
                  </button>

                  <button
                    onClick={() => handleDeleteChat(activeConversation.id)}
                    className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto">
              <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6 sm:px-6 lg:px-8">
                {activeConversation.messages.map((msg) => (
                  <div key={msg.id} className="space-y-3">
                    <div
                      className={`max-w-[90%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                        msg.role === "user"
                          ? "ml-auto bg-[#2563eb] text-white"
                          : "mr-auto border border-white/10 bg-[#111827] text-slate-100"
                      }`}
                    >
                      <MarkdownMessage content={msg.content} />
                    </div>

                    {msg.role === "agent" &&
                      (msg.intent_analysis ||
                        (msg.agent_trace && msg.agent_trace.length > 0)) && (
                        <div className="space-y-2">
                          <button
                            type="button"
                            onClick={() => toggleAgentTrace(msg.id)}
                            className="rounded-full border border-cyan-400/20 bg-cyan-400/5 px-4 py-2 text-xs font-medium text-cyan-100 transition hover:bg-cyan-400/10"
                          >
                            {openAgentTraceByMessageId[msg.id]
                              ? "Hide agent intent"
                              : "Show agent intent"}
                          </button>
                          {openAgentTraceByMessageId[msg.id] && (
                            <AgentTraceCard
                              intentAnalysis={msg.intent_analysis}
                              trace={msg.agent_trace ?? []}
                              isStreaming={msg.isStreaming}
                            />
                          )}
                        </div>
                      )}

                    {msg.display?.show_prediction && msg.prediction && (
                      <PredictionCard
                        prediction={msg.prediction}
                        confidenceLevel={msg.confidence_level}
                      />
                    )}

                    {msg.explanation?.price && (
                      <ExplanationCard
                        explanation={{ price: msg.explanation.price }}
                      />
                    )}

                    {msg.comps &&
                      msg.comps.length > 0 &&
                      msg.display?.show_comps &&
                      !msg.explanation?.price && (
                        <div className="space-y-3">
                          <div className="flex items-center gap-3">
                            <button
                              type="button"
                              onClick={() => toggleComps(msg.id)}
                              className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-slate-200 transition hover:bg-white/10"
                            >
                              {openCompsByMessageId[msg.id]
                                ? "Hide comps"
                                : `Show comps (${msg.comps.length})`}
                            </button>
                          </div>

                          {openCompsByMessageId[msg.id] && (
                            <CompsTable comps={msg.comps} />
                          )}
                        </div>
                      )}
                  </div>
                ))}

                {loading && (
                  <div className="inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200">
                    <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-blue-400" />
                    Working on the next answer...
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-white/10 bg-[#0b1120]/95 px-4 py-4 sm:px-6">
              <div className="mx-auto w-full max-w-3xl">
                <div className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-white/5 p-3 shadow-[0_12px_30px_rgba(0,0,0,0.2)] sm:flex-row sm:items-end">
                  <input
                    className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500"
                    placeholder="Ask for a prediction, comps, or an explanation..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        sendMessage();
                      }
                    }}
                  />

                  <button
                    onClick={sendMessage}
                    disabled={loading}
                    className="rounded-2xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-1 items-center justify-center px-6 py-10">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
                Housing Comps Agent
              </p>
              <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
                Predict a property and inspect the comps behind it.
              </h2>
              <p className="mt-4 text-slate-400">
                Start a chat, enter a subject property, and ask for price,
                comps, or an explanation. The conversation will keep the house
                context as you follow up.
              </p>

              <button
                onClick={handleNewChat}
                className="mt-8 rounded-full bg-white px-6 py-3 font-semibold text-slate-950 transition hover:bg-slate-100"
              >
                Start a new chat
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function renderInlineMarkdown(text: string) {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={index}
          className="rounded border border-white/10 bg-black/30 px-1.5 py-0.5 text-[0.9em] text-cyan-100"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

function MarkdownMessage({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={index} className="text-base font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(4))}
            </h4>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={index} className="text-lg font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(3))}
            </h3>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h2 key={index} className="text-xl font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(2))}
            </h2>
          );
        }

        const bullet = trimmed.match(/^[-*]\s+(.+)/);
        if (bullet) {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-60" />
              <p>{renderInlineMarkdown(bullet[1])}</p>
            </div>
          );
        }

        const numbered = trimmed.match(/^\d+\.\s+(.+)/);
        if (numbered) {
          return (
            <div key={index} className="flex gap-2">
              <span className="min-w-5 text-right text-slate-400">
                {trimmed.split(".")[0]}.
              </span>
              <p>{renderInlineMarkdown(numbered[1])}</p>
            </div>
          );
        }

        return <p key={index}>{renderInlineMarkdown(trimmed)}</p>;
      })}
    </div>
  );
}

function PredictionCard({
  prediction,
  confidenceLevel,
}: {
  prediction: PredictionBand;
  confidenceLevel?: string;
}) {
  const bandWidthPercent = Math.max(
    6,
    Math.min(100, prediction.interval_width_ratio * 100),
  );

  return (
    <div className="max-w-2xl rounded-2xl border border-white/10 bg-[#111827] p-5 text-slate-50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Prediction
          </p>
          <h3 className="mt-2 text-3xl font-semibold">
            {formatCurrency(prediction.predicted_price)}
          </h3>
          <p className="mt-2 text-sm text-slate-400">
            Range {formatCurrency(prediction.predicted_price_low)} to{" "}
            {formatCurrency(prediction.predicted_price_high)}
          </p>
        </div>

        <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right">
          <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
            Confidence
          </p>
          <p className="mt-1 text-lg font-semibold capitalize text-white">
            {confidenceLevel || prediction.confidence_level}
          </p>
        </div>
      </div>

      <div className="mt-5">
        <div className="flex items-center justify-between text-xs text-slate-400">
          <span>Interval width</span>
          <span>{formatPercent(prediction.interval_width_ratio)}</span>
        </div>

        <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-400 to-cyan-400"
            style={{ width: `${bandWidthPercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function AgentTraceCard({
  intentAnalysis,
  trace,
  isStreaming,
}: {
  intentAnalysis?: IntentAnalysis | null;
  trace: AgentTraceEvent[];
  isStreaming?: boolean;
}) {
  return (
    <div className="max-w-3xl rounded-2xl border border-cyan-400/20 bg-cyan-400/5 p-4 text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-cyan-200/80">
            Agent intent
          </p>
          <p className="mt-1 text-sm text-slate-200">
            {intentAnalysis?.summary ?? "Waiting for Gemini intent analysis."}
          </p>
        </div>
        <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs capitalize text-slate-200">
          {intentAnalysis?.intent ?? "thinking"}
          {intentAnalysis?.confidence ? ` / ${intentAnalysis.confidence}` : ""}
        </div>
      </div>

      {intentAnalysis?.planned_tools?.length ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {intentAnalysis.planned_tools.map((tool) => (
            <span
              key={tool}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-cyan-100"
            >
              {tool}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-4 space-y-2">
        {trace.map((event, index) => (
          <div
            key={`${event.step}-${index}`}
            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-[10px] uppercase tracking-[0.2em] text-slate-500">
                {event.step}
              </span>
              {isStreaming && index === trace.length - 1 ? (
                <span className="h-2 w-2 animate-pulse rounded-full bg-cyan-300" />
              ) : null}
            </div>
            <p className="mt-1 text-xs leading-5 text-slate-300">
              {event.detail}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompsTable({ comps }: { comps: Comp[] }) {
  return (
    <div className="max-w-5xl overflow-hidden rounded-2xl border border-white/10 bg-[#111827]">
      <div className="border-b border-white/10 px-5 py-4">
        <p className="text-xs uppercase tracking-[0.25em] text-slate-500">
          Ranked comps
        </p>
      </div>

      <div className="max-h-[520px] overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-slate-400">
            <tr>
              <th className="px-4 py-3 text-left font-medium">Address</th>
              <th className="px-4 py-3 text-right font-medium">Sold price</th>
              <th className="px-4 py-3 text-left font-medium">Built</th>
              <th className="px-4 py-3 text-left font-medium">Sold date</th>
              <th className="px-4 py-3 text-right font-medium">Distance</th>
              <th className="px-4 py-3 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {comps.map((comp, index) => (
              <tr
                key={`${comp.address}-${index}`}
                className="border-t border-white/10"
              >
                <td className="px-4 py-4 text-slate-100">
                  <a
                    href={honestDoorUrl(comp.address)}
                    target="_blank"
                    rel="noreferrer"
                    className="font-medium text-blue-200 underline decoration-blue-300/40 underline-offset-4 transition hover:text-blue-100 hover:decoration-blue-200"
                  >
                    {comp.address}
                  </a>
                </td>
                <td className="px-4 py-4 text-right text-slate-100">
                  {formatCurrency(comp.sold_price)}
                </td>
                <td className="px-4 py-4 text-slate-400">
                  {comp.yearBuilt ?? "n/a"}
                </td>
                <td className="px-4 py-4 text-slate-400">
                  {comp.sold_date || "n/a"}
                </td>
                <td className="px-4 py-4 text-right text-slate-400">
                  {comp.distance_km === null || comp.distance_km === undefined
                    ? "n/a"
                    : `${comp.distance_km.toFixed(1)} km`}
                </td>
                <td className="px-4 py-4 text-right text-slate-100">
                  <div className="flex flex-col items-end gap-2">
                    <span>
                      {((comp.similarity_score ?? 0) * 100).toFixed(1)}%
                    </span>
                    <div className="w-40 space-y-2">
                      <ScoreMini
                        label="Leaf"
                        value={comp.leaf_similarity_score}
                        tone="bg-gradient-to-r from-emerald-400 to-teal-400"
                        subtitle={
                          comp.leaf_matches !== null &&
                          comp.leaf_matches !== undefined &&
                          comp.leaf_count
                            ? `${comp.leaf_matches}/${comp.leaf_count} leaves`
                            : "Leaf overlap"
                        }
                      />
                      <ScoreMini
                        label="PPSF"
                        value={comp.price_per_sqft_similarity}
                        tone="bg-gradient-to-r from-amber-400 to-orange-400"
                        subtitle={`${formatPerSqft(comp.subject_price_per_sqft)} vs ${formatPerSqft(
                          comp.candidate_price_per_sqft,
                        )}`}
                      />
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExplanationCard({ explanation }: { explanation: ExplanationPayload }) {
  const price = explanation.price;
  const comps = null as ExplanationSection | null;

  return (
    <div className="max-w-4xl rounded-2xl border border-white/10 bg-[#111827] p-5 text-slate-50">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-slate-400">
            Explanation
          </p>
          <h3 className="mt-2 text-lg font-semibold text-white">
            Model interpretation
          </h3>
        </div>
      </div>

      {price && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              SHAP price drivers
            </p>
          </div>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            <FeatureBucket
              label="Pushes up"
              features={price.top_positive ?? []}
            />
            <FeatureBucket
              label="Pushes down"
              features={price.top_negative ?? []}
            />
          </div>
        </div>
      )}

      {comps && (
        <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              Comps context
            </p>
            <p className="text-xs text-slate-400">
              Top {comps.top_comp_count ?? 0} comps
            </p>
          </div>
          {comps.top_comp ? (
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">
                Top comp: {comps.top_comp.address}
              </span>
              <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200">
                Score: {(comps.top_comp.similarity_score * 100).toFixed(1)}%
              </span>
            </div>
          ) : null}
          {comps.top_comps?.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {comps.top_comps.slice(0, 3).map((comp) => (
                <span
                  key={comp.address}
                  className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200"
                >
                  {comp.address} · {(comp.similarity_score * 100).toFixed(1)}%
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function FeatureBucket({
  label,
  features,
}: {
  label: string;
  features: ExplanationFeature[];
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
        {label}
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        {features.length ? (
          features.map((feature) => (
            <span
              key={`${feature.feature}-${feature.value}-${feature.direction}`}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-200"
            >
              {feature.feature} = {feature.value} (
              {feature.approx_pct_effect.toFixed(1)}
              %)
            </span>
          ))
        ) : (
          <span className="text-xs text-slate-500">No features returned</span>
        )}
      </div>
    </div>
  );
}

function ScoreMini({
  label,
  value,
  subtitle,
  tone,
}: {
  label: string;
  value?: number | null;
  subtitle: string;
  tone: string;
}) {
  const percent = Math.max(0, Math.min(100, (value ?? 0) * 100));

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-slate-500">
        <span>{label}</span>
        <span>{percent.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${tone}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-[10px] leading-4 text-slate-500">{subtitle}</div>
    </div>
  );
}
