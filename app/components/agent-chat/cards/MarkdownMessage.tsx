import { ReactNode } from "react";

function renderInlineMarkdown(text: string): ReactNode[] {
  return text.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code
          key={index}
          className="rounded border border-white/10 bg-black/30 px-1.5 py-0.5 text-[0.9em] text-cyan-100"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    return part;
  });
}

export default function MarkdownMessage({ content }: { content: string }) {
  const lines = content.split(/\r?\n/);

  return (
    <div className="space-y-2">
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} className="h-2" />;
        }
        if (trimmed.startsWith("### ")) {
          return (
            <h4 key={index} className="text-base font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(4))}
            </h4>
          );
        }
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={index} className="text-lg font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(3))}
            </h3>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h2 key={index} className="text-xl font-semibold text-white">
              {renderInlineMarkdown(trimmed.slice(2))}
            </h2>
          );
        }

        const bullet = trimmed.match(/^[-*]\s+(.+)/);
        if (bullet) {
          return (
            <div key={index} className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-current opacity-60" />
              <p>{renderInlineMarkdown(bullet[1])}</p>
            </div>
          );
        }

        const numbered = trimmed.match(/^\d+\.\s+(.+)/);
        if (numbered) {
          return (
            <div key={index} className="flex gap-2">
              <span className="min-w-5 text-right text-slate-400">
                {trimmed.split(".")[0]}.
              </span>
              <p>{renderInlineMarkdown(numbered[1])}</p>
            </div>
          );
        }

        return <p key={index}>{renderInlineMarkdown(trimmed)}</p>;
      })}
    </div>
  );
}
