import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { AuthLayout } from "../components/AuthLayout";
import { Alert, Button, Field } from "../components/ui";

export function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      await register(form);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err.message || "Unable to create account");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthLayout
      eyebrow="Get started"
      title="Create your account"
      subtitle="Name, email, and a password. You will be signed in right after."
    >
      <form className="grid gap-4" onSubmit={handleSubmit}>
        {error ? <Alert>{error}</Alert> : null}
        <Field
          label="Name"
          name="name"
          type="text"
          autoComplete="name"
          value={form.name}
          onChange={updateField}
          required
          maxLength={120}
        />
        <Field
          label="Email"
          name="email"
          type="email"
          autoComplete="email"
          value={form.email}
          onChange={updateField}
          required
        />
        <Field
          label="Password"
          name="password"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={updateField}
          required
          minLength={8}
          hint="At least 8 characters."
        />
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-5 text-muted">
        Already have an account?{" "}
        <Link className="font-semibold text-harbor" to="/login">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
