import AgentChat from "../components/AgentChat";

export default function AgentPage() {
  return (
    <main className="h-screen w-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(251,191,36,0.18),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,255,255,0.08),_transparent_24%),linear-gradient(180deg,_#04070f_0%,_#09111f_60%,_#02040a_100%)] text-white">
      <div className="h-full w-full overflow-hidden">
        <AgentChat />
      </div>
    </main>
  );
}
