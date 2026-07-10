function unique(values) {
  return values.filter((value, index, array) => value && array.indexOf(value) === index);
}

function localApiBases() {
  if (import.meta.env.VITE_API_URL) return [import.meta.env.VITE_API_URL];
  const host = window.location.hostname;
  const localHosts = new Set(["", "0.0.0.0", "localhost", "127.0.0.1", "::1", "[::1]"]);
  const apiHost = localHosts.has(host) ? "127.0.0.1" : host;
  const protocol = window.location.protocol || "http:";

  return unique([
    `${protocol}//${apiHost}:8000/api`,
    `${protocol}//127.0.0.1:8000/api`,
    `${protocol}//localhost:8000/api`,
    `http://${apiHost}:8000/api`,
    "http://127.0.0.1:8000/api",
    "http://localhost:8000/api",
  ]);
}

const API_BASES = localApiBases();
export const BASE = API_BASES[0];

async function fetchWithFallback(path, options) {
  let lastError;
  for (const base of API_BASES) {
    try {
      return await fetch(base + path, options);
    } catch (err) {
      lastError = err;
    }
  }
  throw lastError || new Error("Backend is not reachable");
}

export async function api(path, options = {}) {
  const token = localStorage.getItem("token");
  const headers = {
    ...(options.body instanceof FormData
      ? {}
      : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };
  let response;
  try {
    response = await fetchWithFallback(path, { ...options, headers });
  } catch {
    throw new Error("Backend is not reachable. Please make sure the Operations Portal backend is running on port 8000.");
  }
  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  }
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      // Preserve the generic message for non-JSON server errors.
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

export function apiUrl(path) {
  return BASE + path;
}

export async function apiBlob(path) {
  const token = localStorage.getItem("token");
  let response;
  try {
    response = await fetchWithFallback(path, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
  } catch {
    throw new Error("Backend is not reachable. Please make sure the Operations Portal backend is running on port 8000.");
  }
  if (!response.ok) throw new Error("Could not load image");
  return response.blob();
}

export async function login(email, password) {
  const body = new URLSearchParams({ username: email, password });
  return api("/auth/login", {
    method: "POST",
    body,
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
}

export async function downloadAttachment(ticketId, attachment) {
  const token = localStorage.getItem("token");
  let response;
  try {
    response = await fetchWithFallback(
      `/tickets/${ticketId}/attachments/${attachment.id}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
  } catch {
    throw new Error("Backend is not reachable. Please make sure the Operations Portal backend is running on port 8000.");
  }
  if (!response.ok) throw new Error("Could not download this attachment");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = attachment.original_name;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function downloadProtected(path, filename) {
  const token = localStorage.getItem("token");
  let response;
  try {
    response = await fetchWithFallback(path, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    throw new Error("Backend is not reachable. Please make sure the Operations Portal backend is running on port 8000.");
  }
  if (!response.ok) throw new Error("Could not export this report");
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
