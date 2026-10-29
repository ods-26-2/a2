import React, { useState, useEffect, useCallback } from 'react';
import LoginPage from './pages/LoginPage';
import QRCodePage from './pages/QRCodePage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import {
  getSavedSession,
  saveSession,
  clearSession,
  getCachedPayload,
  setCachedPayload,
  fetchLatestPayload,
} from './services/api';
import { getAdminSession, clearAdminSession } from './services/adminApi';

function checkIsAdmin() {
  const path = window.location.pathname.toLowerCase();
  const hash = window.location.hash.toLowerCase();
  return path.includes('/admin') || hash.includes('/admin') || hash === '#admin';
}

export default function App() {
  const [isAdmin, setIsAdmin] = useState(() => checkIsAdmin());
  const [adminSession, setAdminSession] = useState(() => getAdminSession());
  const [session, setSession] = useState(() => getSavedSession());
  const [payload, setPayload] = useState(() => getCachedPayload());
  const [loadingPayload, setLoadingPayload] = useState(false);

  useEffect(() => {
    const handleLocationChange = () => {
      setIsAdmin(checkIsAdmin());
      setAdminSession(getAdminSession());
    };

    window.addEventListener('popstate', handleLocationChange);
    window.addEventListener('hashchange', handleLocationChange);
    return () => {
      window.removeEventListener('popstate', handleLocationChange);
      window.removeEventListener('hashchange', handleLocationChange);
    };
  }, []);

  const syncPayload = useCallback(async (cpf, password) => {
    try {
      setLoadingPayload(true);
      const latest = await fetchLatestPayload(cpf, password);
      setPayload(latest);
      setCachedPayload(latest);
    } catch (err) {
      console.warn('Erro ao atualizar payload em segundo plano:', err.message);
      if (!getCachedPayload()) {
        clearSession();
        setSession(null);
      }
    } finally {
      setLoadingPayload(false);
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) {
      const saved = getSavedSession();
      if (saved?.cpf && saved?.password) {
        syncPayload(saved.cpf, saved.password);
      }
    }
  }, [isAdmin, syncPayload]);

  const handleLoginSuccess = async (cpf, password) => {
    const freshPayload = await fetchLatestPayload(cpf, password);
    saveSession(cpf, password);
    setCachedPayload(freshPayload);
    setSession({ cpf, password });
    setPayload(freshPayload);
  };

  const handleLogout = () => {
    clearSession();
    setSession(null);
    setPayload(null);
  };

  const handleAdminLogout = () => {
    clearAdminSession();
    setAdminSession(null);
  };

  const handleNavigateToUserApp = () => {
    if (window.location.hash.includes('admin')) {
      window.location.hash = '';
    } else {
      window.history.pushState({}, '', '/app/');
    }
    setIsAdmin(false);
  };

  // Se a rota for /admin, avalia sessão segura de administrador
  if (isAdmin) {
    if (adminSession?.token) {
      return (
        <AdminDashboardPage
          adminUser={adminSession}
          onLogout={handleAdminLogout}
          onNavigateToApp={handleNavigateToUserApp}
        />
      );
    }
    return (
      <AdminLoginPage
        onLoginSuccess={(data) => setAdminSession(data)}
        onNavigateToApp={handleNavigateToUserApp}
      />
    );
  }

  // Interface do usuário comum (sem link visível para /admin)
  return (
    <div className="w-full h-full bg-[#F0F0F0] flex flex-col relative overflow-hidden">
      {session?.cpf ? (
        <QRCodePage
          cpf={session.cpf}
          payload={payload}
          loadingPayload={loadingPayload}
          onLogout={handleLogout}
        />
      ) : (
        <LoginPage onLoginSuccess={handleLoginSuccess} />
      )}
    </div>
  );
}
