export default function EmptyChatState({
  onNewChat,
}: {
  onNewChat: () => void;
}) {
  return (
    <div className="flex flex-1 items-center justify-center px-6 py-10">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-xs uppercase tracking-[0.3em] text-slate-500">
          Housing Comps Agent (Cap-comps)
        </p>
        <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
          Predict a property and inspect the comps behind it.
        </h2>
        <p className="mt-4 text-slate-400">
          Start a chat, enter a subject property, and ask for price, comps, or
          an explanation. The conversation will keep the house context as you
          follow up.
        </p>

        <button
          onClick={onNewChat}
          className="mt-8 rounded-full bg-white px-6 py-3 font-semibold text-slate-950 transition hover:bg-slate-100"
        >
          Start a new chat
        </button>
      </div>
    </div>
  );
}
