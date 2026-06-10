import { AgentTraceEvent, IntentAnalysis } from "../types";

export default function AgentTraceCard({
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
