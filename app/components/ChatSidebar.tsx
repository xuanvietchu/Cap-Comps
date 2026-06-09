import { HouseDetails } from "./HouseDetailsForm";

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
}: {
  conversations: Conversation[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
}) {
  return (
    <aside className="w-72 border-r border-gray-800 bg-gray-950 p-4 flex flex-col">
      <button
        onClick={onNewChat}
        className="w-full bg-blue-600 hover:bg-blue-700 rounded-xl px-4 py-3 font-semibold mb-4"
      >
        + New Chat
      </button>

      <div className="space-y-2 overflow-y-auto">
        {conversations.map((conv) => (
          <button
            key={conv.id}
            onClick={() => onSelectChat(conv.id)}
            className={`w-full text-left p-3 rounded-xl ${
              conv.id === activeId
                ? "bg-gray-800 text-white"
                : "text-gray-400 hover:bg-gray-900"
            }`}
          >
            <div className="font-medium truncate">{conv.title}</div>
            <div className="text-xs text-gray-500 truncate">
              {conv.houseDetails.assessmentClass} ·{" "}
              {conv.houseDetails.houseStyle}
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}
