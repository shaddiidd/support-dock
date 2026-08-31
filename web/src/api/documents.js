import { request, requestForm } from "./client";

export function listDocuments(token, businessId) {
  return request(`/api/v1/businesses/${businessId}/documents`, { token });
}

export function uploadDocument(token, businessId, file) {
  return requestForm(`/api/v1/businesses/${businessId}/documents`, {
    token,
    file,
  });
}

export function replaceDocument(token, businessId, documentId, file) {
  return requestForm(
    `/api/v1/businesses/${businessId}/documents/${documentId}/replace`,
    { token, file }
  );
}

export function reindexDocument(token, businessId, documentId) {
  return request(`/api/v1/businesses/${businessId}/documents/${documentId}/reindex`, {
    method: "POST",
    token,
  });
}

export function deleteDocument(token, businessId, documentId) {
  return request(`/api/v1/businesses/${businessId}/documents/${documentId}`, {
    method: "DELETE",
    token,
  });
}

export function getDownloadUrl(token, businessId, documentId) {
  return request(`/api/v1/businesses/${businessId}/documents/${documentId}/download`, {
    token,
  });
}
