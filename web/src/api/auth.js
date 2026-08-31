import { request } from "./client";

export function register(payload) {
  return request("/api/v1/auth/register", {
    method: "POST",
    body: payload,
  });
}

export function login(payload) {
  return request("/api/v1/auth/login", {
    method: "POST",
    body: payload,
  });
}

export function getCurrentUser(token) {
  return request("/api/v1/auth/me", { token });
}
