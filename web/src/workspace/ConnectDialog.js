import { useState } from "react";
import { HiOutlineClipboard, HiOutlineClipboardDocumentCheck } from "react-icons/hi2";

import { widgetChatPath } from "../api/chat";
import { API_URL } from "../api/client";
import { Dialog } from "../components/Dialog";
import { Alert, Button } from "../components/ui";
import { useBusinessDialogs } from "./BusinessDialogs";

export function ConnectDialog({ open, business, onClose }) {
  const { openEdit } = useBusinessDialogs();
  const [copied, setCopied] = useState("");

  if (!business) {
    return null;
  }

  const origin = business.website_origin || originFromUrl(business.website_url);
  const endpoint = business.widget_url || `${API_URL}${widgetChatPath(business.id)}`;
  const snippet = buildSnippet(endpoint);

  async function copy(label, value) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(label);
      window.setTimeout(() => setCopied(""), 1800);
    } catch {
      setCopied("");
    }
  }

  return (
    <Dialog
      open={open}
      wide
      title="Connect chat"
      description="Embed this assistant on your website. Requests are only accepted from the origin you saved."
      onClose={onClose}
    >
      {!origin ? (
        <div className="grid gap-4">
          <Alert tone="warning">
            Add your website URL in business settings first. Chat will only
            answer from that origin.
          </Alert>
          <div className="flex justify-end">
            <Button
              type="button"
              onClick={() => {
                onClose();
                openEdit(business);
              }}
            >
              Add website URL
            </Button>
          </div>
        </div>
      ) : (
        <div className="grid gap-5">
          <ol className="grid list-decimal gap-2 pl-5 text-sm leading-relaxed text-ink">
            <li>
              Call the endpoint below with <code className="rounded bg-paper px-1 py-0.5 text-xs">fetch</code> from pages on{" "}
              <span className="font-semibold">{origin}</span> only.
            </li>
            <li>No API key. The browser Origin header must match this business.</li>
            <li>Other websites cannot use this chat, and this origin cannot reach another business.</li>
            <li>
              Reuse the same <code className="rounded bg-paper px-1 py-0.5 text-xs">conversation_id</code> for a
              session. Send prior turns in <code className="rounded bg-paper px-1 py-0.5 text-xs">history</code> as{" "}
              <code className="rounded bg-paper px-1 py-0.5 text-xs">{`{ role, content }`}</code>. Do not include the
              current message in history.
            </li>
            <li>
              Show <code className="rounded bg-paper px-1 py-0.5 text-xs">reply</code> to the customer. Keep{" "}
              <code className="rounded bg-paper px-1 py-0.5 text-xs">conversation_id</code> for the session. If{" "}
              <code className="rounded bg-paper px-1 py-0.5 text-xs">chat_closed</code> is true, stop the chat.
            </li>
          </ol>

          <CopyBlock
            label="Allowed origin"
            value={origin}
            copied={copied === "origin"}
            onCopy={() => copy("origin", origin)}
          />
          <CopyBlock
            label="Chat URL"
            value={`POST ${endpoint}`}
            copied={copied === "url"}
            onCopy={() => copy("url", endpoint)}
            hint="This is the API host the dashboard is talking to. After deploy it follows your public API, or PUBLIC_API_URL if you set one."
          />
          <CopyBlock
            label="Request"
            value={snippet}
            copied={copied === "snippet"}
            onCopy={() => copy("snippet", snippet)}
            multiline
          />
          <CopyBlock
            label="Response"
            value={EXAMPLE_RESPONSE}
            copied={copied === "response"}
            onCopy={() => copy("response", EXAMPLE_RESPONSE)}
            multiline
            hint="When a ticket is opened, chat_closed is true and ticket includes number, title, and status."
          />
        </div>
      )}
    </Dialog>
  );
}

function CopyBlock({ label, value, copied, onCopy, multiline = false, hint }) {
  return (
    <div className="grid gap-1.5">
      <div className="flex items-center justify-between gap-3">
        <p className="text-xs font-bold uppercase tracking-[0.14em] text-muted">{label}</p>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 text-xs font-semibold text-muted hover:bg-paper hover:text-ink"
        >
          {copied ? (
            <HiOutlineClipboardDocumentCheck className="h-4 w-4" />
          ) : (
            <HiOutlineClipboard className="h-4 w-4" />
          )}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre
        className={
          multiline
            ? "overflow-x-auto whitespace-pre rounded-xl bg-harbor-deep p-4 text-xs leading-relaxed text-paper"
            : "overflow-x-auto whitespace-pre-wrap break-all rounded-xl bg-harbor-deep p-4 text-xs leading-relaxed text-paper"
        }
      >
        {value}
      </pre>
      {hint ? <p className="text-xs font-medium leading-relaxed text-muted">{hint}</p> : null}
    </div>
  );
}

function originFromUrl(url) {
  if (!url) {
    return "";
  }
  try {
    return new URL(url).origin;
  } catch {
    return "";
  }
}

function buildSnippet(endpoint) {
  return `const conversationId = crypto.randomUUID();
const history = [];

async function sendChat(message) {
  const data = await fetch("${endpoint}", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      history
    })
  }).then((res) => res.json());

  history.push({ role: "user", content: message });
  history.push({ role: "assistant", content: data.reply });
  return data;
}

await sendChat("How can I reset my password?");
// history is now:
// [
//   { role: "user", content: "How can I reset my password?" },
//   { role: "assistant", content: "Open Settings, then tap Reset password." }
// ]
await sendChat("That did not work. What next?");`;
}

const EXAMPLE_RESPONSE = `{
  "reply": "Open Settings, then tap Reset password.",
  "refused": false,
  "sources": [
    {
      "document_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      "document_title": "Account help",
      "heading_path": "Reset password"
    }
  ],
  "conversation_id": "11111111-1111-4111-8111-111111111111",
  "chat_closed": false,
  "ticket": null
}`;
