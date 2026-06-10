import AgentTraceCard from "./cards/AgentTraceCard";
import CompsTable from "./cards/CompsTable";
import CsvExportCard from "./cards/CsvExportCard";
import ExplanationCard from "./cards/ExplanationCard";
import MarkdownMessage from "./cards/MarkdownMessage";
import PredictionCard from "./cards/PredictionCard";
import { Conversation } from "./types";

export default function AgentMessageList({
  activeConversation,
  loading,
  openAgentTraceByMessageId,
  openCompsByMessageId,
  onToggleAgentTrace,
  onToggleComps,
}: {
  activeConversation: Conversation;
  loading: boolean;
  openAgentTraceByMessageId: Record<string, boolean>;
  openCompsByMessageId: Record<string, boolean>;
  onToggleAgentTrace: (messageId: string) => void;
  onToggleComps: (messageId: string) => void;
}) {
  return (
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
                    onClick={() => onToggleAgentTrace(msg.id)}
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
              <PredictionCard prediction={msg.prediction} />
            )}

            {msg.explanation?.price && (
              <ExplanationCard explanation={{ price: msg.explanation.price }} />
            )}

            {msg.display?.show_csv_export && msg.export_csv && (
              <CsvExportCard exportCsv={msg.export_csv} />
            )}

            {msg.comps &&
              msg.comps.length > 0 &&
              msg.display?.show_comps &&
              !msg.explanation?.price && (
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => onToggleComps(msg.id)}
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
  );
}
