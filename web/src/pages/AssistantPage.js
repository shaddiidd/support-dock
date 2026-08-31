import { useEffect, useState } from "react";

import { Alert, Button, Eyebrow, Field } from "../components/ui";
import { useBusinesses } from "../workspace/BusinessContext";

export function AssistantPage({ business }) {
  const { updateBusiness } = useBusinesses();
  const [draft, setDraft] = useState(business.assistant_instructions || "");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDraft(business.assistant_instructions || "");
    setError("");
    setNotice("");
  }, [business.id]);

  useEffect(() => {
    setDraft(business.assistant_instructions || "");
  }, [business.assistant_instructions]);

  const dirty = draft.trim() !== (business.assistant_instructions || "").trim();

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setSaving(true);
    try {
      await updateBusiness(business.id, {
        assistant_instructions: draft.trim() || null,
      });
      setNotice("Assistant instructions saved.");
    } catch (err) {
      setError(err.message || "Unable to save instructions");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-full min-h-0 overflow-y-auto px-6 py-6">
      <form className="mx-auto grid max-w-3xl gap-4" onSubmit={handleSubmit}>
        <div>
          <Eyebrow className="mb-1 text-muted">Assistant</Eyebrow>
          <h2 className="text-lg font-bold">Instructions</h2>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            Extra rules for this workspace: tone, things to watch for, or when
            to escalate. These cannot invent facts or replace your documents.
          </p>
        </div>
        {error ? <Alert>{error}</Alert> : null}
        {notice ? <Alert tone="success">{notice}</Alert> : null}
        <Field
          label="Instructions"
          name="assistant_instructions"
          as="textarea"
          value={draft}
          onChange={(event) => {
            setDraft(event.target.value);
            setNotice("");
          }}
          maxLength={4000}
          rows={12}
          hint={`${draft.trim().length} / 4000`}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={saving || !dirty}>
            {saving ? "Saving…" : "Save instructions"}
          </Button>
        </div>
      </form>
    </div>
  );
}
