import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders the LLM's markdown-formatted answer as actual HTML (bold, bullet/
 * numbered lists, tables via remark-gfm) instead of showing raw "**text**"/
 * "*" characters. Component overrides below just apply the same `ink` dark-
 * on-white-card palette and spacing used everywhere else in the answer card.
 */
export default function MarkdownAnswer({ text }: { text: string }) {
  return (
    <div className="text-sm text-ink">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-2 leading-relaxed last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
          em: ({ children }) => <em className="italic">{children}</em>,
          ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-accent underline hover:text-accent-hover">
              {children}
            </a>
          ),
          code: ({ children }) => (
            <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-[13px] text-ink">{children}</code>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mb-2 border-l-2 border-gray-200 pl-3 text-ink-muted last:mb-0">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="mb-2 overflow-x-auto last:mb-0">
              <table className="min-w-full divide-y divide-gray-200 text-sm">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="whitespace-nowrap px-2 py-1 text-left font-medium text-ink-muted">{children}</th>
          ),
          td: ({ children }) => <td className="whitespace-nowrap px-2 py-1 text-ink">{children}</td>,
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
