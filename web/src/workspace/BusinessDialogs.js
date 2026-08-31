import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Dialog } from "../components/Dialog";
import { Alert, Button, Field } from "../components/ui";
import { useBusinesses } from "./BusinessContext";
import { DEFAULT_TAB, isWorkspaceTab, workspacePath } from "./paths";

const BusinessDialogContext = createContext(null);

export function BusinessDialogProvider({ children }) {
  const [dialog, setDialog] = useState({ type: null, business: null });

  const close = useCallback(() => {
    setDialog({ type: null, business: null });
  }, []);

  const value = {
    openCreate: () => setDialog({ type: "create", business: null }),
    openEdit: (business) => setDialog({ type: "edit", business }),
    openDelete: (business) => setDialog({ type: "delete", business }),
    close,
  };

  return (
    <BusinessDialogContext.Provider value={value}>
      {children}
      <CreateBusinessDialog open={dialog.type === "create"} onClose={close} />
      <EditBusinessDialog
        key={dialog.business?.id || "edit"}
        open={dialog.type === "edit"}
        business={dialog.business}
        onClose={close}
      />
      <DeleteBusinessDialog
        open={dialog.type === "delete"}
        business={dialog.business}
        onClose={close}
      />
    </BusinessDialogContext.Provider>
  );
}

export function useBusinessDialogs() {
  const context = useContext(BusinessDialogContext);
  if (!context) {
    throw new Error("useBusinessDialogs must be used within BusinessDialogProvider");
  }
  return context;
}

function CreateBusinessDialog({ open, onClose }) {
  const navigate = useNavigate();
  const { createBusiness } = useBusinesses();
  const [form, setForm] = useState({
    name: "",
    description: "",
    website_url: "",
    support_email: "",
    contact_email: "",
    contact_phone: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setForm({
        name: "",
        description: "",
        website_url: "",
        support_email: "",
        contact_email: "",
        contact_phone: "",
      });
      setError("");
      setSubmitting(false);
    }
  }, [open]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const created =       await createBusiness({
        name: form.name,
        description: form.description,
        website_url: form.website_url.trim(),
        support_email: form.support_email.trim() || null,
        contact_email: form.contact_email.trim() || null,
        contact_phone: form.contact_phone.trim() || null,
      });
      onClose();
      navigate(workspacePath(created.id));
    } catch (err) {
      setError(err.message || "Unable to create business");
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      title="New business"
      description="Create a workspace you can switch to from the sidebar. Chat will only load on this website."
      onClose={onClose}
    >
      <BusinessForm
        form={form}
        setForm={setForm}
        error={error}
        submitting={submitting}
        submitLabel="Create business"
        websiteRequired
        onSubmit={handleSubmit}
        onCancel={onClose}
      />
    </Dialog>
  );
}

function EditBusinessDialog({ open, business, onClose }) {
  const { updateBusiness } = useBusinesses();
  const [form, setForm] = useState({
    name: business?.name || "",
    description: business?.description || "",
    website_url: business?.website_url || "",
    support_email: business?.support_email || "",
    contact_email: business?.contact_email || "",
    contact_phone: business?.contact_phone || "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!business) {
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      await updateBusiness(business.id, {
        name: form.name,
        description: form.description,
        website_url: form.website_url.trim() || null,
        support_email: form.support_email.trim() || null,
        contact_email: form.contact_email.trim() || null,
        contact_phone: form.contact_phone.trim() || null,
      });
      onClose();
    } catch (err) {
      setError(err.message || "Unable to update business");
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      title="Edit business"
      description="Update this workspace name, website, and contact details."
      onClose={onClose}
    >
      <BusinessForm
        form={form}
        setForm={setForm}
        error={error}
        submitting={submitting}
        submitLabel="Save changes"
        websiteRequired
        onSubmit={handleSubmit}
        onCancel={onClose}
      />
    </Dialog>
  );
}

function DeleteBusinessDialog({ open, business, onClose }) {
  const navigate = useNavigate();
  const { businessId, tab } = useParams();
  const { businesses, deleteBusiness } = useBusinesses();
  const currentTab = isWorkspaceTab(tab) ? tab : DEFAULT_TAB;
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) {
      setError("");
      setSubmitting(false);
    }
  }, [open]);

  async function handleDelete() {
    if (!business) {
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      const remaining = businesses.filter((item) => item.id !== business.id);
      await deleteBusiness(business.id);
      onClose();
      if (business.id === businessId) {
        if (remaining[0]) {
          navigate(workspacePath(remaining[0].id, currentTab), { replace: true });
        } else {
          navigate("/", { replace: true });
        }
      }
    } catch (err) {
      setError(err.message || "Unable to delete business");
      setSubmitting(false);
    }
  }

  return (
    <Dialog
      open={open}
      title="Delete business"
      description={
        business
          ? `Delete “${business.name}”? This cannot be undone.`
          : "This cannot be undone."
      }
      onClose={onClose}
    >
      {error ? <Alert>{error}</Alert> : null}
      <div className="mt-2 flex flex-wrap justify-end gap-3">
        <Button type="button" variant="quiet" onClick={onClose}>
          Cancel
        </Button>
        <Button type="button" variant="danger" onClick={handleDelete} disabled={submitting}>
          {submitting ? "Deleting…" : "Delete business"}
        </Button>
      </div>
    </Dialog>
  );
}

function BusinessForm({
  form,
  setForm,
  error,
  submitting,
  submitLabel,
  onSubmit,
  onCancel,
  websiteRequired = false,
}) {
  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  return (
    <form className="grid gap-4" onSubmit={onSubmit}>
      {error ? <Alert>{error}</Alert> : null}
      <Field
        label="Business name"
        name="name"
        value={form.name}
        onChange={updateField}
        required
        maxLength={120}
        autoFocus
      />
      <Field
        label="Website URL"
        name="website_url"
        value={form.website_url || ""}
        onChange={updateField}
        required={websiteRequired}
        maxLength={500}
        placeholder="https://example.com"
        hint="Customers can only open this chat from this site. Used for CORS and shown by the assistant."
      />
      <Field
        label="Description"
        name="description"
        as="textarea"
        value={form.description}
        onChange={updateField}
        maxLength={500}
        rows={3}
      />
      <Field
        label="Support email"
        name="support_email"
        type="email"
        value={form.support_email || ""}
        onChange={updateField}
        hint="Tickets are emailed here when the assistant escalates to a human."
      />
      <Field
        label="Public email"
        name="contact_email"
        type="email"
        value={form.contact_email || ""}
        onChange={updateField}
        hint="Shared when customers ask how to reach you. The ticket inbox is never shown to the assistant."
      />
      <Field
        label="Public phone"
        name="contact_phone"
        value={form.contact_phone || ""}
        onChange={updateField}
        maxLength={40}
        hint="Shared with customers who ask for a phone number."
      />
      <div className="flex flex-wrap justify-end gap-3">
        <Button type="button" variant="quiet" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? "Saving…" : submitLabel}
        </Button>
      </div>
    </form>
  );
}
