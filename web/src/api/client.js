export const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

function readErrorMessage(payload) {
  const detail = payload?.detail;
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(". ");
  }
  return "Request failed";
}

export async function request(path, { method = "GET", body, token } = {}) {
  const headers = { Accept: "application/json" };
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const payload =
    response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(readErrorMessage(payload));
    error.status = response.status;
    throw error;
  }

  return payload;
}

export async function requestForm(path, { method = "POST", file, token, fieldName = "file" } = {}) {
  const headers = { Accept: "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const body = new FormData();
  body.append(fieldName, file);

  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body,
  });

  const payload =
    response.status === 204 ? {} : await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(readErrorMessage(payload));
    error.status = response.status;
    throw error;
  }

  return payload;
}
