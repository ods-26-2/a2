/**
 * Crachá QR Code - Web Frontend
 * Autenticação por CPF e exibição da payload de 32 bytes via /get-payload
 */

let qrCodeInstance = null;
let currentPayloadData = null;

const STORAGE_SESSION_KEY = "cracha_session_auth";
const STORAGE_CACHED_PAYLOAD_KEY = "cracha_cached_payload";

// Determina a URL base da API
const API_BASE = (window.location.protocol.startsWith("http") && window.location.port === "8080")
  ? ""
  : "http://localhost:8080";

document.addEventListener("DOMContentLoaded", () => {
  const session = getSavedSession();
  if (session && session.cpf && session.password) {
    document.documentElement.classList.add("is-logged");
    
    // Tenta renderizar imediatamente a partir do cache para zero atraso visual
    const cachedPayload = getCachedPayload();
    if (cachedPayload) {
      showQR(session.cpf, cachedPayload);
    }
    
    // Sincroniza em segundo plano com o backend
    autoLogin(session.cpf, session.password);
  } else {
    document.documentElement.classList.remove("is-logged");
    showLogin();
  }
});

function getSavedSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_SESSION_KEY) || localStorage.getItem(STORAGE_SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function saveSession(cpf, password) {
  const payload = JSON.stringify({ cpf, password });
  sessionStorage.setItem(STORAGE_SESSION_KEY, payload);
  localStorage.setItem(STORAGE_SESSION_KEY, payload);
  document.documentElement.classList.add("is-logged");
}

function clearSession() {
  sessionStorage.removeItem(STORAGE_SESSION_KEY);
  localStorage.removeItem(STORAGE_SESSION_KEY);
  sessionStorage.removeItem(STORAGE_CACHED_PAYLOAD_KEY);
  document.documentElement.classList.remove("is-logged");
}

function getCachedPayload() {
  try {
    const raw = sessionStorage.getItem(STORAGE_CACHED_PAYLOAD_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function setCachedPayload(payload) {
  try {
    sessionStorage.setItem(STORAGE_CACHED_PAYLOAD_KEY, JSON.stringify(payload));
  } catch (e) {}
}

function maskCPF(input) {
  let v = input.value.replace(/\D/g, "");
  if (v.length > 11) v = v.substring(0, 11);
  if (v.length > 9) {
    v = v.replace(/(\d{3})(\d{3})(\d{3})(\d{1,2})/, "$1.$2.$3-$4");
  } else if (v.length > 6) {
    v = v.replace(/(\d{3})(\d{3})(\d{1,3})/, "$1.$2.$3");
  } else if (v.length > 3) {
    v = v.replace(/(\d{3})(\d{1,3})/, "$1.$2");
  }
  input.value = v;
}

function formatCpfDisplay(cpf) {
  const v = cpf.toString().replace(/\D/g, "");
  if (v.length === 11) {
    return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
  }
  return v || cpf;
}

function formatValidity(startDateStr, endDateStr) {
  try {
    const start = new Date(startDateStr);
    const end = new Date(endDateStr);

    const pad = (n) => String(n).padStart(2, "0");
    const day = pad(start.getDate());
    const month = pad(start.getMonth() + 1);
    const year = start.getFullYear();

    const startHour = `${pad(start.getHours())}:${pad(start.getMinutes())}`;
    const endHour = `${pad(end.getHours())}:${pad(end.getMinutes())}`;

    return `${day}/${month}/${year} • ${startHour} às ${endHour}`;
  } catch (e) {
    return `${startDateStr} às ${endDateStr}`;
  }
}

function hexToBytes(hex) {
  if (!hex) return new Uint8Array(16);
  if (hex instanceof Uint8Array) return hex;
  if (typeof hex === "string") {
    const clean = hex.trim();
    // Hex de tamanho par (32 chars = 16 bytes | 64 chars = 32 bytes)
    if (/^[0-9a-fA-F]+$/.test(clean) && clean.length % 2 === 0) {
      const bytes = new Uint8Array(clean.length / 2);
      for (let i = 0; i < clean.length; i += 2) {
        bytes[i / 2] = parseInt(clean.substring(i, i + 2), 16);
      }
      return bytes;
    }
  }
  return hex;
}

async function fetchLatestPayload(cpf, password) {
  const cleanCpf = cpf.toString().replace(/\D/g, "");
  const url = `${API_BASE}/get-payload?cpf=${encodeURIComponent(cleanCpf)}&password=${encodeURIComponent(password)}`;

  const response = await fetch(url, {
    method: "GET",
    headers: { "Accept": "application/json" },
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

async function handleLogin(e) {
  if (e) e.preventDefault();
  const errorBox = document.getElementById("loginError");
  errorBox.style.display = "none";

  const cpfInput = document.getElementById("cpf");
  const passInput = document.getElementById("password");
  const btn = document.getElementById("btnEntrar");
  const btnText = document.getElementById("btnText");

  const rawCpf = cpfInput ? cpfInput.value.trim() : "";
  const password = passInput ? passInput.value : "";
  const cleanCpf = rawCpf.replace(/\D/g, "");

  if (!cleanCpf) {
    showError("Por favor, informe o CPF.");
    return;
  }

  btn.disabled = true;
  btnText.textContent = "Validando...";

  try {
    const payload = await fetchLatestPayload(cleanCpf, password);
    saveSession(cleanCpf, password);
    setCachedPayload(payload);
    showQR(cleanCpf, payload);
  } catch (err) {
    showError(err.message || "Erro ao conectar com o servidor.");
  } finally {
    btn.disabled = false;
    btnText.textContent = "Entrar";
  }
}

async function autoLogin(cpf, password) {
  try {
    const payload = await fetchLatestPayload(cpf, password);
    setCachedPayload(payload);
    showQR(cpf, payload);
  } catch (err) {
    clearSession();
    showLogin();
    showError(err.message || "Sessão inválida. Faça login novamente.");
  }
}

function showError(msg) {
  const errorBox = document.getElementById("loginError");
  if (errorBox) {
    errorBox.textContent = msg;
    errorBox.style.display = "block";
  }
}

function handleLogout() {
  clearSession();
  showLogin();
}

function showLogin() {
  document.documentElement.classList.remove("is-logged");
  const loginView = document.getElementById("loginView");
  const qrView = document.getElementById("qrView");
  if (loginView) loginView.style.display = "flex";
  if (qrView) qrView.style.display = "none";
}

function showQR(cpf, payload) {
  document.documentElement.classList.add("is-logged");
  const loginView = document.getElementById("loginView");
  const qrView = document.getElementById("qrView");
  if (loginView) loginView.style.display = "none";
  if (qrView) qrView.style.display = "flex";

  const display = document.getElementById("displayCpf");
  if (display) display.textContent = formatCpfDisplay(cpf);

  updateQRDisplay(payload);
}

function updateQRDisplay(payload) {
  currentPayloadData = payload;

  // Atualiza texto de validade
  const validityEl = document.getElementById("validityDisplay");
  if (validityEl && payload.startDate && payload.endDate) {
    validityEl.textContent = formatValidity(payload.startDate, payload.endDate);
  }

  const box = document.getElementById("qrcode");
  if (!box) return;

  const size = Math.min(box.clientWidth || 320, box.clientHeight || 320) || 320;
  box.innerHTML = "";

  // Converte a payload criptografada (hex de 32 chars) para os 16 bytes binários exatos
  const rawBytes = hexToBytes(payload.data);

  // QR Code otimizado para 16 bytes:
  // Versão 1 (21x21) com Error Correction Level L acomoda até 17 bytes em modo byte
  // (o menor possível para os 16 bytes da payload criptografada).
  qrCodeInstance = new QRCode(box, {
    text: rawBytes,
    width: size,
    height: size,
    typeNumber: 1,
    colorDark: "#000000",
    colorLight: "#F0F0F0",
    correctLevel: QRCode.CorrectLevel.L,
  });
}

window.addEventListener("resize", () => {
  if (document.documentElement.classList.contains("is-logged") && currentPayloadData) {
    updateQRDisplay(currentPayloadData);
  }
});
