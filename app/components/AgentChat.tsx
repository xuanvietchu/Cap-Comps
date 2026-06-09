"use client";

import { useState } from "react";
import ChatSidebar from "./ChatSidebar";
import HouseDetailsForm from "./HouseDetailsForm";
import { HouseDetails } from "./houseDetails";

type Message = {
  role: "user" | "agent";
  content: string;
  comps?: Comp[];
};

type Comp = {
  address: string;
  sold_price: number;
  sold_date: string;
  distance_km: number;
  similarity_score: number;
  reasons?: string[];
};

type Conversation = {
  id: string;
  title: string;
  houseDetails: HouseDetails;
  messages: Message[];
};

export default function AgentChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingConversationId, setEditingConversationId] = useState<
    string | null
  >(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const activeConversation = conversations.find((c) => c.id === activeId);

  function handleNewChat() {
    setActiveId(null);
    setShowForm(true);
  }

  function handleCancelForm() {
    setShowForm(false);
  }

  function handleCreateChat(houseDetails: HouseDetails) {
    const id = crypto.randomUUID();

    const newConversation: Conversation = {
      id,
      title: houseDetails.address || "New Comps Search",
      houseDetails,
      messages: [
        {
          role: "agent",
          content:
            "House details saved. Ask me to find comps, explain valuation support, or compare market context.",
        },
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
                title: details.neighbourhoodName || conv.title,
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

  async function sendMessage() {
    if (!input.trim() || !activeConversation) return;

    const messageToSend = input;

    const userMessage: Message = {
      role: "user",
      content: messageToSend,
    };

    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === activeConversation.id
          ? { ...conv, messages: [...conv.messages, userMessage] }
          : conv,
      ),
    );

    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageToSend,
          house_details: activeConversation.houseDetails,
          conversation_id: activeConversation.id,
        }),
      });

      const data = await res.json();

      const agentMessage: Message = {
        role: "agent",
        content: data.answer ?? "I found some results.",
        comps: data.comps ?? [],
      };

      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === activeConversation.id
            ? { ...conv, messages: [...conv.messages, agentMessage] }
            : conv,
        ),
      );
    } catch {
      setConversations((prev) =>
        prev.map((conv) =>
          conv.id === activeConversation.id
            ? {
                ...conv,
                messages: [
                  ...conv.messages,
                  {
                    role: "agent",
                    content: "Error connecting to the agent backend.",
                  },
                ],
              }
            : conv,
        ),
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="h-[700px] bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden flex">
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onNewChat={handleNewChat}
        onSelectChat={(id) => {
          setActiveId(id);
          setShowForm(false);
        }}
      />

      <section className="flex-1 flex flex-col">
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
            <div className="border-b border-gray-800 p-4 flex items-center justify-between">
              <div>
                <h2 className="font-semibold">{activeConversation.title}</h2>
                <p className="text-sm text-gray-400">
                  {activeConversation.houseDetails.bedroomsCount} bed ·{" "}
                  {activeConversation.houseDetails.bathroomsCount} bath ·{" "}
                  {activeConversation.houseDetails.livingArea} sqft
                </p>
              </div>

              <button
                onClick={() => {
                  setEditingConversationId(activeConversation.id);
                  setShowForm(true);
                }}
                className="bg-gray-800 hover:bg-gray-700 px-4 py-2 rounded-xl text-sm"
              >
                Edit Details
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-5">
              {activeConversation.messages.map((msg, index) => (
                <div key={index}>
                  <div
                    className={`max-w-3xl rounded-xl p-4 ${
                      msg.role === "user"
                        ? "ml-auto bg-blue-600"
                        : "mr-auto bg-gray-800"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {msg.comps && msg.comps.length > 0 && (
                    <CompsTable comps={msg.comps} />
                  )}
                </div>
              ))}

              {loading && (
                <div className="bg-gray-800 rounded-xl p-4 w-fit">
                  Finding comps...
                </div>
              )}
            </div>

            <div className="border-t border-gray-800 p-4 flex gap-3">
              <input
                className="flex-1 bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 outline-none"
                placeholder="Ask about comps, valuation, or market context..."
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
                className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-xl font-semibold"
              >
                Send
              </button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-center text-gray-400">
            <div>
              <h2 className="text-2xl font-bold text-white mb-2">
                House Comps Agent
              </h2>
              <p>Start a new chat to enter house details.</p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function CompsTable({ comps }: { comps: Comp[] }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-xl border border-gray-800">
      <table className="w-full text-sm">
        <thead className="bg-gray-800 text-gray-300">
          <tr>
            <th className="p-3 text-left">Address</th>
            <th className="p-3 text-right">Sold Price</th>
            <th className="p-3 text-left">Sold Date</th>
            <th className="p-3 text-right">Distance</th>
            <th className="p-3 text-right">Similarity</th>
            <th className="p-3 text-left">Reasons</th>
          </tr>
        </thead>

        <tbody>
          {comps.map((comp, index) => (
            <tr key={index} className="border-t border-gray-800">
              <td className="p-3">{comp.address}</td>
              <td className="p-3 text-right">
                ${comp.sold_price.toLocaleString()}
              </td>
              <td className="p-3">{comp.sold_date}</td>
              <td className="p-3 text-right">{comp.distance_km} km</td>
              <td className="p-3 text-right">
                {(comp.similarity_score * 100).toFixed(1)}%
              </td>
              <td className="p-3 text-gray-300">
                {comp.reasons?.join(", ") ?? "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
