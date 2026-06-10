import { Conversation, Message } from "./types";

export const STORAGE_KEY = "kv-housing-comps-conversations";
export const HISTORY_MESSAGE_LIMIT = 16;

export function createId() {
  return crypto.randomUUID();
}

export function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatPerSqft(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "n/a";
  }

  return `${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value)}/sqft`;
}

export function honestDoorUrl(address: string) {
  const slug = address.trim().toLowerCase().replace(/\s+/g, "-");
  return `https://www.honestdoor.com/property/${encodeURIComponent(
    `${slug}-edmonton-ab`,
  )}`;
}

export function normalizeMessage(
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
      show_csv_export: message.display?.show_csv_export ?? false,
    },
    intent_analysis: message.intent_analysis ?? null,
    agent_trace: message.agent_trace ?? [],
    export_csv: message.export_csv ?? null,
    isStreaming: message.isStreaming ?? false,
  };
}

export function normalizeConversation(raw: Partial<Conversation>): Conversation {
  return {
    id: raw.id || createId(),
    title: raw.title || "New comps search",
    houseDetails: raw.houseDetails as Conversation["houseDetails"],
    messages: (raw.messages || []).map((message) =>
      normalizeMessage(message, message.role === "user" ? "user" : "agent"),
    ),
  };
}

export function loadStoredConversations() {
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

export function buildConversationHistory(messages: Message[]) {
  return messages
    .filter((message) => !message.isStreaming && message.content.trim())
    .slice(-HISTORY_MESSAGE_LIMIT)
    .map((message) => ({
      role: message.role === "agent" ? "assistant" : message.role,
      content: message.content,
    }));
}
