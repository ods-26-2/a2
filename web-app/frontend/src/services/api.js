const STORAGE_SESSION_KEY = "cracha_session_auth";
const STORAGE_CACHED_PAYLOAD_KEY = "cracha_cached_payload";

export function getSavedSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function saveSession(cpf) {
  sessionStorage.setItem(STORAGE_SESSION_KEY, JSON.stringify({ cpf }));
}

export function clearSession() {
  sessionStorage.removeItem(STORAGE_SESSION_KEY);
  sessionStorage.removeItem(STORAGE_CACHED_PAYLOAD_KEY);
}

export async function userLogin(cpf, password) {
  const response = await fetch("/api/user/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ cpf: Number(String(cpf).replace(/\\D/g, "")), password }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || "Falha na autenticação");
  }
  return response.json();
}

export async function userLogout() {
  try {
    await fetch("/api/user/logout", { method: "POST", credentials: "include" });
  } catch (_) {}
  clearSession();
}

export async function fetchUserMe() {
  const response = await fetch("/api/user/me", { credentials: "include" });
  if (!response.ok) return null;
  return response.json();
}

export function getCachedPayload() {
  try {
    const raw = sessionStorage.getItem(STORAGE_CACHED_PAYLOAD_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function setCachedPayload(payload) {
  try {
    sessionStorage.setItem(STORAGE_CACHED_PAYLOAD_KEY, JSON.stringify(payload));
  } catch (e) {}
}

export async function fetchLatestPayload(cpf, password) {
  const cleanCpf = cpf ? String(cpf).replace(/\D/g, "") : "";
  const body = password
    ? JSON.stringify({ cpf: Number(cleanCpf), password })
    : (cleanCpf ? JSON.stringify({ cpf: Number(cleanCpf) }) : null);

  const response = await fetch("/get-payload", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    credentials: "include",
    body: body || undefined,
  });

  if (!response.ok) {
    let errorDetail = "Falha na autenticação";
    try {
      const errJson = await response.json();
      if (errJson && errJson.detail) errorDetail = errJson.detail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  const result = await response.json();
  const payloadItem = Array.isArray(result) ? result[0] : result;

  if (!payloadItem || !payloadItem.data) {
    throw new Error("Nenhum acesso disponível no momento para este usuário");
  }

  return payloadItem;
}
