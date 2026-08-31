import { useEffect, useRef, useState } from "react";
import { HiOutlinePaperAirplane } from "react-icons/hi2";

import * as chatApi from "../api/chat";
import { useAuth } from "../auth/AuthContext";
import { Alert, Button, Eyebrow, cn } from "./ui";

function newConversationId() {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  const hex = Date.now().toString(16).padStart(12, "0").slice(-12);
  return `00000000-0000-4000-8000-${hex}`;
}

function welcome(name) {
  return {
    role: "assistant",
    content: `Hello. How can I help you with ${name} today?`,
    refused: false,
    sources: [],
  };
}

export function ChatPanel({ business, onTicketCreated }) {
  const { token } = useAuth();
  const listRef = useRef(null);
  const [conversationId, setConversationId] = useState(newConversationId);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState(() => [welcome(business.name)]);
  const [sending, setSending] = useState(false);
  const [closed, setClosed] = useState(false);
  const [ticket, setTicket] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const node = listRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages, sending]);

  function startNewConversation() {
    setConversationId(newConversationId());
    setMessages([welcome(business.name)]);
    setClosed(false);
    setTicket(null);
    setDraft("");
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || sending || closed) {
      return;
    }

    const history = messages
      .filter((item) => item.role === "user" || item.role === "assistant")
      .slice(-12)
      .map((item) => ({ role: item.role, content: item.content }));

    setDraft("");
    setError("");
    setSending(true);
    setMessages((current) => [...current, { role: "user", content: text }]);

    try {
      const response = await chatApi.sendChat(token, business.id, {
        message: text,
        history,
        conversation_id: conversationId,
      });
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.reply,
          refused: Boolean(response.refused),
          sources: response.sources || [],
        },
      ]);
      if (response.chat_closed) {
        setClosed(true);
        setTicket(response.ticket || null);
        if (response.ticket && onTicketCreated) {
          onTicketCreated(response.ticket);
        }
      }
    } catch (err) {
      setError(err.message || "Unable to send that message");
      setMessages((current) => current.slice(0, -1));
      setDraft(text);
    } finally {
      setSending(false);
    }
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="mx-auto flex h-full min-h-0 w-full min-w-0 max-w-3xl flex-col">
      <header className="shrink-0 border-b border-line px-4 py-4 sm:px-6">
        <Eyebrow className="mb-1">Testing only</Eyebrow>
        <h2 className="text-lg font-bold">Try the {business.name} assistant</h2>
        <p className="mt-1 text-sm leading-relaxed text-muted">
          This chat is for testing in the dashboard. Live customer chat will live
          elsewhere.
        </p>
      </header>

      <div ref={listRef} className="grid min-h-0 flex-1 content-start gap-3 overflow-auto px-4 py-4 sm:px-6">
        {messages.map((item, index) => (
          <ChatBubble key={`${item.role}-${index}`} message={item} />
        ))}
        {sending ? (
          <p className="text-sm text-muted" role="status">
            Thinking…
          </p>
        ) : null}
        {closed ? (
          <Alert tone="success">
            {ticket
              ? `Ticket ${ticket.number} is open and this test conversation is closed.`
              : "This test conversation is closed."}
          </Alert>
        ) : null}
      </div>

      <form className="shrink-0 border-t border-line p-4 pb-[max(1rem,env(safe-area-inset-bottom))]" onSubmit={handleSubmit}>
        {error ? <p className="mb-3 text-sm text-red-800">{error}</p> : null}
        {closed ? (
          <Button type="button" className="w-full py-2.5" onClick={startNewConversation}>
            Start new test conversation
          </Button>
        ) : (
          <>
            <label className="sr-only" htmlFor="chat-message">
              Message
            </label>
            <textarea
              id="chat-message"
              className="mb-3 h-20 w-full resize-none rounded-xl border border-line bg-paper px-3.5 py-3 text-sm outline-none focus:outline focus:outline-2 focus:outline-offset-1 focus:outline-harbor sm:h-24"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask a question, or try a payment failure and include your email…"
              maxLength={4000}
            />
            <Button type="submit" className="w-full py-2.5" disabled={sending || !draft.trim()}>
              <span className="inline-flex items-center justify-center gap-2">
                <HiOutlinePaperAirplane className="h-4 w-4" />
                {sending ? "Sending…" : "Send"}
              </span>
            </Button>
          </>
        )}
      </form>
    </div>
  );
}

function ChatBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("max-w-[min(92%,36rem)] break-words", isUser ? "ml-auto" : "")}>
      <div
        className={cn(
          "rounded-2xl px-3.5 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-harbor text-paper"
            : message.refused
              ? "bg-paper text-muted"
              : "bg-paper text-ink"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        ) : (
          <MarkdownBody content={message.content} />
        )}
      </div>
      {!isUser && message.sources?.length ? (
        <p className="mt-1.5 text-xs text-muted">
          From {message.sources.map((source) => source.document_title).join(", ")}
        </p>
      ) : null}
    </div>
  );
}

function MarkdownBody({ content }) {
  return (
    <div className="space-y-2 [&_ol]:list-decimal [&_ul]:list-disc [&_ol]:space-y-1 [&_ul]:space-y-1 [&_ol]:pl-5 [&_ul]:pl-5">
      {parseBlocks(content).map((block, index) => {
        if (block.type === "ul" || block.type === "ol") {
          const List = block.type === "ol" ? "ol" : "ul";
          return (
            <List key={index}>
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineText text={item} />
                </li>
              ))}
            </List>
          );
        }
        return (
          <p key={index}>
            <InlineText text={block.text} />
          </p>
        );
      })}
    </div>
  );
}

function InlineText({ text }) {
  const chunks = String(text).split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).filter(Boolean);
  return chunks.map((chunk, index) => {
    if (chunk.startsWith("**") && chunk.endsWith("**") && chunk.length > 4) {
      return <strong key={index}>{chunk.slice(2, -2)}</strong>;
    }
    if (chunk.startsWith("*") && chunk.endsWith("*") && chunk.length > 2) {
      return <em key={index}>{chunk.slice(1, -1)}</em>;
    }
    if (chunk.startsWith("`") && chunk.endsWith("`") && chunk.length > 2) {
      return (
        <code key={index} className="rounded bg-line/60 px-1 py-0.5 text-[0.85em]">
          {chunk.slice(1, -1)}
        </code>
      );
    }
    return <span key={index}>{chunk}</span>;
  });
}

function parseBlocks(content) {
  const lines = String(content || "").replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+\.\s+(.*)$/);
    if (bullet || numbered) {
      const ordered = Boolean(numbered);
      const items = [];
      while (index < lines.length) {
        const match = ordered
          ? lines[index].match(/^\s*\d+\.\s+(.*)$/)
          : lines[index].match(/^\s*[-*]\s+(.*)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        index += 1;
      }
      blocks.push({ type: ordered ? "ol" : "ul", items });
      continue;
    }

    const paragraph = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !/^\s*[-*]\s+/.test(lines[index]) &&
      !/^\s*\d+\.\s+/.test(lines[index])
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: "p", text: paragraph.join(" ") });
  }

  return blocks.length ? blocks : [{ type: "p", text: "" }];
}
