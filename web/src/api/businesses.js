import { request } from "./client";

export function listBusinesses(token) {
  return request("/api/v1/businesses", { token });
}

export function createBusiness(token, payload) {
  return request("/api/v1/businesses", {
    method: "POST",
    token,
    body: payload,
  });
}

export function updateBusiness(token, businessId, payload) {
  return request(`/api/v1/businesses/${businessId}`, {
    method: "PATCH",
    token,
    body: payload,
  });
}

export function deleteBusiness(token, businessId) {
  return request(`/api/v1/businesses/${businessId}`, {
    method: "DELETE",
    token,
  });
}
