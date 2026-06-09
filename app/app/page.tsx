import AgentChat from "../components/AgentChat";

export default function AgentPage() {
  return (
    <main className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold mb-2">House Comps Agent</h1>
        <p className="text-gray-400 mb-6">
          Ask for comparable sold properties and valuation support
        </p>

        <AgentChat />
      </div>
    </main>
  );
}
