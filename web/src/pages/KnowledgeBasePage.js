import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  HiOutlineArrowPath,
  HiOutlineArrowDownTray,
  HiOutlineDocumentText,
  HiOutlineTrash,
} from "react-icons/hi2";

import * as documentsApi from "../api/documents";
import { useAuth } from "../auth/AuthContext";
import { Dialog } from "../components/Dialog";
import { Alert, Button } from "../components/ui";

const ACCEPT = ".pdf,.docx,.txt,.md,.markdown,.html,.htm";
const PROCESSING = new Set(["uploaded", "processing"]);

const STATUS_STYLES = {
  uploaded: "bg-paper text-muted",
  processing: "bg-amber-50 text-amber-900",
  ready: "bg-emerald-50 text-emerald-800",
  failed: "bg-red-50 text-red-800",
};

const STATUS_LABELS = {
  uploaded: "Uploaded",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const STATE_LABELS = {
  queued: "Waiting to process",
  extracting: "Extracting text",
  chunking: "Splitting into chunks",
  embedding: "Creating embeddings",
  indexing: "Indexing for search",
  complete: "Indexed",
  failed: "Failed",
};

export function KnowledgeBasePage({ business }) {
  const { token } = useAuth();
  const fileInputRef = useRef(null);
  const replaceInputRef = useRef(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [uploading, setUploading] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [pendingDelete, setPendingDelete] = useState(null);
  const [pendingReplace, setPendingReplace] = useState(null);
  const [replaceFile, setReplaceFile] = useState(null);

  const refresh = useCallback(async () => {
    const items = await documentsApi.listDocuments(token, business.id);
    setDocuments(items);
    return items;
  }, [token, business.id]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    setNotice("");
    setDocuments([]);
    refresh()
      .catch((err) => {
        if (!cancelled) {
          setError(err.message || "Unable to load documents");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const isBusy = useMemo(
    () => documents.some((item) => PROCESSING.has(item.status)),
    [documents]
  );

  useEffect(() => {
    if (!isBusy) {
      return undefined;
    }
    const timer = setInterval(() => {
      refresh().catch(() => {});
    }, 2500);
    return () => clearInterval(timer);
  }, [isBusy, refresh]);

  async function handleUpload(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (files.length === 0) {
      return;
    }
    setError("");
    setNotice("");
    setUploading(true);
    const failures = [];
    try {
      for (const file of files) {
        try {
          await documentsApi.uploadDocument(token, business.id, file);
        } catch (err) {
          failures.push(`${file.name}: ${err.message || "Upload failed"}`);
        }
      }
      await refresh();
      if (failures.length) {
        setError(failures.join(" "));
      } else {
        setNotice(
          files.length === 1
            ? "Document uploaded. Indexing will continue in the background."
            : "Documents uploaded. Indexing will continue in the background."
        );
      }
    } finally {
      setUploading(false);
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) {
      return;
    }
    setError("");
    setBusyId(pendingDelete.id);
    try {
      await documentsApi.deleteDocument(token, business.id, pendingDelete.id);
      setDocuments((current) => current.filter((item) => item.id !== pendingDelete.id));
      setPendingDelete(null);
      setNotice("Document deleted from storage, search index, and this workspace.");
    } catch (err) {
      setError(err.message || "Unable to delete document");
    } finally {
      setBusyId("");
    }
  }

  function startReplace(document) {
    setPendingReplace(document);
    setReplaceFile(null);
  }

  async function confirmReplace() {
    if (!pendingReplace || !replaceFile) {
      return;
    }
    setError("");
    setBusyId(pendingReplace.id);
    try {
      await documentsApi.replaceDocument(
        token,
        business.id,
        pendingReplace.id,
        replaceFile
      );
      await refresh();
      setPendingReplace(null);
      setReplaceFile(null);
      setNotice("Replacement uploaded. The previous file and index were removed.");
    } catch (err) {
      setError(err.message || "Unable to replace document");
    } finally {
      setBusyId("");
    }
  }

  async function handleRetry(document) {
    setError("");
    setBusyId(document.id);
    try {
      await documentsApi.reindexDocument(token, business.id, document.id);
      await refresh();
    } catch (err) {
      setError(err.message || "Unable to retry indexing");
    } finally {
      setBusyId("");
    }
  }

  async function handleDownload(document) {
    setError("");
    try {
      const payload = await documentsApi.getDownloadUrl(token, business.id, document.id);
      window.open(payload.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(err.message || "Unable to download this file");
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 flex-wrap items-start justify-between gap-4 border-b border-line px-6 py-4">
        <div className="min-w-0">
          <h2 className="text-lg font-bold">Knowledge base</h2>
          <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
            PDF, Word, Markdown, HTML, and text files up to 20 MB. Each file stays
            private to this workspace.
          </p>
        </div>
          <Button
            type="button"
            className="shrink-0 py-2.5"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Upload documents"}
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept={ACCEPT}
            multiple
            onChange={handleUpload}
          />
          <input
            ref={replaceInputRef}
            type="file"
            className="hidden"
            accept={ACCEPT}
            onChange={(event) => {
              const file = event.target.files?.[0] || null;
              event.target.value = "";
              setReplaceFile(file);
            }}
          />
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-4">
          <div className="grid gap-3">
            {error ? <Alert>{error}</Alert> : null}
            {notice ? <Alert tone="success">{notice}</Alert> : null}
            {isBusy ? (
              <Alert tone="warning">
                Documents are still being processed. This list will update automatically.
              </Alert>
            ) : null}
          </div>

          <div className="mt-4">
            {loading ? (
              <p className="text-muted">Loading documents…</p>
            ) : documents.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-line px-6 py-16 text-center">
                <HiOutlineDocumentText className="mx-auto h-8 w-8 text-muted" />
                <p className="mt-3 font-semibold">No documents yet</p>
                <p className="mt-1 text-sm text-muted">
                  Add help articles, FAQs, or troubleshooting guides.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-line border-y border-line">
                {documents.map((document) => (
                  <DocumentCard
                    key={document.id}
                    document={document}
                    busy={busyId === document.id}
                    onReplace={() => startReplace(document)}
                    onDelete={() => setPendingDelete(document)}
                    onRetry={() => handleRetry(document)}
                    onDownload={() => handleDownload(document)}
                  />
                ))}
              </ul>
            )}
          </div>
        </div>

        <Dialog
          open={Boolean(pendingDelete)}
          title="Delete document"
          description={
            pendingDelete
              ? `Delete “${pendingDelete.filename}”? The original file, search vectors, and workspace record will be permanently removed.`
              : "This cannot be undone."
          }
          onClose={() => setPendingDelete(null)}
        >
          <div className="mt-2 flex flex-wrap justify-end gap-3">
            <Button type="button" variant="quiet" onClick={() => setPendingDelete(null)}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="danger"
              onClick={confirmDelete}
              disabled={Boolean(busyId)}
            >
              {busyId ? "Deleting…" : "Delete permanently"}
            </Button>
          </div>
        </Dialog>

        <Dialog
          open={Boolean(pendingReplace)}
          title="Replace document"
          description={
            pendingReplace
              ? `Replace “${pendingReplace.filename}”? The current file and its indexed chunks will be removed before the new file is processed.`
              : "Choose a replacement file."
          }
          onClose={() => {
            setPendingReplace(null);
            setReplaceFile(null);
          }}
        >
          <div className="grid gap-4">
            <p className="text-sm text-muted">
              {replaceFile
                ? `Selected file: ${replaceFile.name}`
                : "Choose a PDF, Word, Markdown, HTML, or text file."}
            </p>
            <div className="flex flex-wrap justify-end gap-3">
              <Button
                type="button"
                variant="quiet"
                onClick={() => replaceInputRef.current?.click()}
              >
                Choose file
              </Button>
              <Button
                type="button"
                onClick={confirmReplace}
                disabled={!replaceFile || Boolean(busyId)}
              >
                {busyId ? "Replacing…" : "Replace and reindex"}
              </Button>
            </div>
          </div>
        </Dialog>
    </div>
  );
}

function DocumentCard({ document, busy, onReplace, onDelete, onRetry, onDownload }) {
  const status = STATUS_LABELS[document.status] || document.status;
  const state = STATE_LABELS[document.processing_state] || document.processing_state;
  const failed = document.status === "failed";

  return (
    <li className="py-3.5">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate font-semibold">{document.filename}</p>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${
                STATUS_STYLES[document.status] || STATUS_STYLES.uploaded
              }`}
            >
              {status}
            </span>
          </div>
          <p className="mt-1 text-sm text-muted">
            {formatBytes(document.size_bytes)} · {formatDate(document.created_at)} ·{" "}
            {document.status === "ready"
              ? `${document.indexed_chunk_count} chunk${
                  document.indexed_chunk_count === 1 ? "" : "s"
                }`
              : state}
          </p>
          {failed && document.error_message ? (
            <p className="mt-2 text-sm text-red-800">{document.error_message}</p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Button type="button" variant="quiet" className="px-3 py-2" onClick={onDownload}>
            <span className="inline-flex items-center gap-1.5">
              <HiOutlineArrowDownTray className="h-4 w-4" />
              Original
            </span>
          </Button>
          {failed ? (
            <Button
              type="button"
              variant="quiet"
              className="px-3 py-2"
              onClick={onRetry}
              disabled={busy}
            >
              <span className="inline-flex items-center gap-1.5">
                <HiOutlineArrowPath className="h-4 w-4" />
                Retry
              </span>
            </Button>
          ) : (
            <Button
              type="button"
              variant="quiet"
              className="px-3 py-2"
              onClick={onReplace}
              disabled={busy || PROCESSING.has(document.status)}
            >
              Replace
            </Button>
          )}
          <Button
            type="button"
            variant="danger"
            className="px-3 py-2"
            onClick={onDelete}
            disabled={busy}
          >
            <span className="inline-flex items-center gap-1.5">
              <HiOutlineTrash className="h-4 w-4" />
              Delete
            </span>
          </Button>
        </div>
      </div>
    </li>
  );
}

function formatBytes(value) {
  if (!value && value !== 0) {
    return "Unknown size";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
