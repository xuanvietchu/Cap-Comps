export default function AgentChatInput({
  input,
  loading,
  onInputChange,
  onSend,
}: {
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
}) {
  return (
    <div className="border-t border-white/10 bg-[#0b1120]/95 px-4 py-4 sm:px-6">
      <div className="mx-auto w-full max-w-3xl">
        <div className="flex flex-col gap-3 rounded-3xl border border-white/10 bg-white/5 p-3 shadow-[0_12px_30px_rgba(0,0,0,0.2)] sm:flex-row sm:items-end">
          <input
            className="min-w-0 flex-1 bg-transparent px-3 py-2 text-sm text-white outline-none placeholder:text-slate-500"
            placeholder="Ask for a prediction, comps, or an explanation..."
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                onSend();
              }
            }}
          />

          <button
            onClick={onSend}
            disabled={loading}
            className="rounded-2xl bg-white px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
