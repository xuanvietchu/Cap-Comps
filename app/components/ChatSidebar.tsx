import { HouseDetails } from "./houseDetails";

type Conversation = {
  id: string;
  title: string;
  houseDetails: HouseDetails;
};

export default function ChatSidebar({
  conversations,
  activeId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
}) {
  return (
    <aside className="flex h-full min-h-0 w-72 flex-col border-r border-white/10 bg-[#0f172a] p-3 sm:p-4">
      <button
        onClick={onNewChat}
        className="mb-4 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-left font-semibold text-white transition hover:bg-white/10"
      >
        New Chat
      </button>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`w-full rounded-2xl p-3 transition ${
              conv.id === activeId
                ? "border border-white/10 bg-white/10 text-white"
                : "border border-transparent text-slate-300 hover:bg-white/5"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelectChat(conv.id)}
              className="w-full text-left"
            >
              <div className="truncate font-medium">{conv.title}</div>
              <div className="truncate text-xs text-slate-400">
                {conv.houseDetails.assessmentClass} / {conv.houseDetails.houseStyle}
              </div>
            </button>

            <button
              type="button"
              onClick={() => onDeleteChat(conv.id)}
              className="mt-3 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
            >
              Delete chat
            </button>
          </div>
        ))}
      </div>
    </aside>
  );
}
