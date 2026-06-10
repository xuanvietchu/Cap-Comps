import { Conversation } from "./types";

export default function AgentChatHeader({
  activeConversation,
  onEdit,
  onDelete,
}: {
  activeConversation: Conversation;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="border-b border-white/10 px-4 py-4 sm:px-6">
      <div className="mx-auto flex w-full max-w-3xl items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-400">
            Housing Comps Agent
          </p>
          <h2 className="mt-2 text-xl font-semibold text-white">
            {activeConversation.title}
          </h2>
          <p className="mt-1 text-sm text-slate-400">
            {activeConversation.houseDetails.bedroomsCount} bed /{" "}
            {activeConversation.houseDetails.bathroomsCount} bath /{" "}
            {activeConversation.houseDetails.livingArea} sqft
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onEdit}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
          >
            Edit
          </button>

          <button
            onClick={onDelete}
            className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
