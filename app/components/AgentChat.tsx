"use client";

import { useState } from "react";

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
  living_area?: number;
  bedrooms?: number;
  bathrooms?: number;
  reasons?: string[];
};

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "agent",
      content:
        "Hi, I can help find house comps. Try: Find comps for 11153 52 Street NW, Edmonton.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage() {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: input,
        }),
      });

      const data = await res.json();

      const agentMessage: Message = {
        role: "agent",
        content: data.answer ?? "I found some results.",
        comps: data.comps ?? [],
      };

      setMessages((prev) => [...prev, agentMessage]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "agent",
          content: "Error connecting to the agent backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
      <div className="h-[600px] overflow-y-auto p-5 space-y-5">
        {messages.map((msg, index) => (
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
          placeholder="Ask: Find comps for an address..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") sendMessage();
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
