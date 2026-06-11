"use client";

import { useEffect, useMemo, useState } from "react";

import AgentChatHeader from "./agent-chat/AgentChatHeader";
import AgentChatInput from "./agent-chat/AgentChatInput";
import AgentMessageList from "./agent-chat/AgentMessageList";
import {
  AgentTraceEvent,
  Conversation,
  IntentAnalysis,
} from "./agent-chat/types";
import {
  buildConversationHistory,
  createId,
  loadStoredConversations,
  normalizeMessage,
  STORAGE_KEY,
} from "./agent-chat/utils";
import ChatSidebar from "./ChatSidebar";
import EmptyChatState from "./agent-chat/EmptyChatState";
import HouseDetailsForm from "./HouseDetailsForm";
import { HouseDetails } from "./houseDetails";

function backendUrl(path: string) {
  const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configuredUrl) {
    return `${configuredUrl.replace(/\/$/, "")}${path}`;
  }

  const host =
    typeof window === "undefined" || !window.location.hostname
      ? "localhost"
      : window.location.hostname;
  return `http://${host}:8000${path}`;
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
              "Hello, my name is Cap-comps, your trusty housing comps AI Agent. Your House details are saved. Ask me for subject price evaluation, top 10 comps, or an explanation on price and evaluation.",
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
    // Stream trace events first, then replace the pending message with the final payload.
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
      const res = await fetch(backendUrl("/chat/stream"), {
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
                                export_csv: data.export_csv ?? null,
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
            <AgentChatHeader
              activeConversation={activeConversation}
              onEdit={() => {
                setEditingConversationId(activeConversation.id);
                setShowForm(true);
              }}
              onDelete={() => handleDeleteChat(activeConversation.id)}
            />

            <AgentMessageList
              activeConversation={activeConversation}
              loading={loading}
              openAgentTraceByMessageId={openAgentTraceByMessageId}
              openCompsByMessageId={openCompsByMessageId}
              onToggleAgentTrace={toggleAgentTrace}
              onToggleComps={toggleComps}
            />

            <AgentChatInput
              input={input}
              loading={loading}
              onInputChange={setInput}
              onSend={sendMessage}
            />
          </>
        ) : (
          <EmptyChatState onNewChat={handleNewChat} />
        )}
      </section>
    </div>
  );
}
