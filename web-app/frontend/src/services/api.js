const STORAGE_SESSION_KEY = "cracha_session_auth";
const STORAGE_CACHED_PAYLOAD_KEY = "cracha_cached_payload";

export function getSavedSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_SESSION_KEY) || localStorage.getItem(STORAGE_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function saveSession(cpf, password) {
  const payload = JSON.stringify({ cpf, password });
  sessionStorage.setItem(STORAGE_SESSION_KEY, payload);
  localStorage.setItem(STORAGE_SESSION_KEY, payload);
}

export function clearSession() {
  sessionStorage.removeItem(STORAGE_SESSION_KEY);
  localStorage.removeItem(STORAGE_SESSION_KEY);
  sessionStorage.removeItem(STORAGE_CACHED_PAYLOAD_KEY);
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
  const cleanCpf = String(cpf).replace(/\D/g, "");

  const response = await fetch("/get-payload", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      cpf: Number(cleanCpf),
      password,
    }),
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
