const STORAGE_ADMIN_TOKEN_KEY = "cracha_admin_auth";

export function getAdminSession() {
  try {
    const raw = sessionStorage.getItem(STORAGE_ADMIN_TOKEN_KEY) || localStorage.getItem(STORAGE_ADMIN_TOKEN_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

export function saveAdminSession(token, username) {
  const payload = JSON.stringify({ token, username });
  sessionStorage.setItem(STORAGE_ADMIN_TOKEN_KEY, payload);
  localStorage.setItem(STORAGE_ADMIN_TOKEN_KEY, payload);
}

export function clearAdminSession() {
  sessionStorage.removeItem(STORAGE_ADMIN_TOKEN_KEY);
  localStorage.removeItem(STORAGE_ADMIN_TOKEN_KEY);
}

function getAuthHeaders() {
  const session = getAdminSession();
  const headers = { 'Content-Type': 'application/json' };
  if (session?.token) {
    headers['Authorization'] = `Bearer ${session.token}`;
  }
  return headers;
}

async function handleResponse(res) {
  if (res.status === 401) {
    clearAdminSession();
    throw new Error('Sessão expirada. Faça login novamente.');
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Erro na requisição');
  }
  return res.json();
}

export async function adminLogin(username, password) {
  const res = await fetch('/api/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Usuário ou senha inválidos');
  }
  const data = await res.json();
  if (data?.token) {
    saveAdminSession(data.token, data.username);
  }
  return data;
}

export async function adminLogout() {
  try {
    await fetch('/api/admin/logout', {
      method: 'POST',
      headers: getAuthHeaders(),
    });
  } catch (_) {}
  clearAdminSession();
}

export async function checkAdminMe() {
  const res = await fetch('/api/admin/me', {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function fetchAdminUsers() {
  const res = await fetch('/api/admin/users', {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function fetchAdminStats() {
  const res = await fetch('/api/admin/stats', {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function createOrUpdateAdminUser(userData) {
  const res = await fetch('/api/admin/users', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(userData),
  });
  return handleResponse(res);
}

export async function toggleUserActive(cpf) {
  const cleanCpf = String(cpf).replace(/\D/g, '');
  const res = await fetch(`/api/admin/users/${cleanCpf}/toggle`, {
    method: 'PUT',
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function deleteAdminUser(cpf) {
  const cleanCpf = String(cpf).replace(/\D/g, '');
  const res = await fetch(`/api/admin/users/${cleanCpf}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function updateUserExpiration(cpf, expirationDate) {
  const cleanCpf = String(cpf).replace(/\D/g, '');
  const res = await fetch(`/api/admin/users/${cleanCpf}/expiration`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ expiration_date: expirationDate || null }),
  });
  return handleResponse(res);
}

export async function fetchAdminConfig() {
  const res = await fetch('/api/admin/config', {
    headers: getAuthHeaders(),
  });
  return handleResponse(res);
}

export async function updateAdminConfig(payloadBatchSize) {
  const res = await fetch('/api/admin/config', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ payload_batch_size: Number(payloadBatchSize) }),
  });
  return handleResponse(res);
}

export async function changeAdminPassword(currentPassword, newPassword) {
  const res = await fetch('/api/admin/change-password', {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
  return handleResponse(res);
}
