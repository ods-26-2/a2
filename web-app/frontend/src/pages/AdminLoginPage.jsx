import React, { useState } from 'react';
import { ShieldCheck, User, Lock, ArrowRight, Loader2, QrCode, Eye, EyeOff } from 'lucide-react';
import { adminLogin } from '../services/adminApi';

export default function AdminLoginPage({ onLoginSuccess, onNavigateToApp }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!username.trim()) {
      setError('Por favor, informe o usuário de administrador.');
      return;
    }
    if (!password) {
      setError('Por favor, informe a senha de administrador.');
      return;
    }

    setLoading(true);
    try {
      const data = await adminLogin(username.trim(), password);
      onLoginSuccess(data);
    } catch (err) {
      setError(err.message || 'Falha na autenticação');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col justify-center items-center bg-[#F8FAFC] pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] px-5 select-none">
      <div className="w-full max-w-[390px] py-8 px-6 sm:px-8 bg-white border border-[#E2E8F0] rounded-[16px] shadow-[0_12px_32px_-8px_rgba(15,23,42,0.08)] flex flex-col">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3.5">
            <div className="w-13 h-13 rounded-[12px] bg-blue-50 text-[#2563EB] flex items-center justify-center border border-blue-100 shadow-2xs">
              <ShieldCheck className="w-7 h-7" strokeWidth={2.2} />
            </div>
          </div>
          <h2 className="text-[20px] font-bold text-[#0F172A] tracking-tight">
            Painel Admin
          </h2>
          <p className="text-[13px] text-[#64748B] mt-1 font-medium">
            Acesso restrito ao gerenciamento do sistema
          </p>
        </div>

        {/* Error Notification */}
        {error && (
          <div className="bg-[#FEE2E2] border border-[#F87171] text-[#B91C1C] px-3.5 py-2.5 rounded-[8px] text-[13px] font-medium text-center mb-4 animate-in fade-in duration-200">
            {error}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="adminUser" className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
              Usuário
            </label>
            <div className="relative flex items-center">
              <User className="absolute left-3.5 w-[18px] h-[18px] text-[#9CA3AF] pointer-events-none" />
              <input
                type="text"
                id="adminUser"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nome de usuário"
                required
                autoComplete="username"
                className="w-full py-3.5 pl-11 pr-3.5 bg-white border border-[#D1D5DB] rounded-[8px] text-[#111827] text-base shadow-xs focus:outline-none focus:border-[#2563EB] focus:ring-3 focus:ring-[#2563EB]/15 transition-all"
              />
            </div>
          </div>

          <div>
            <label htmlFor="adminPassword" className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
              Senha
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-[18px] h-[18px] text-[#9CA3AF] pointer-events-none" />
              <input
                type={showPassword ? 'text' : 'password'}
                id="adminPassword"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Senha de acesso"
                required
                autoComplete="current-password"
                className="w-full py-3.5 pl-11 pr-11 bg-white border border-[#D1D5DB] rounded-[8px] text-[#111827] text-base shadow-xs focus:outline-none focus:border-[#2563EB] focus:ring-3 focus:ring-[#2563EB]/15 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
                className="absolute right-3.5 text-[#9CA3AF] hover:text-[#4B5563] cursor-pointer"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] active:scale-[0.98] disabled:opacity-65 disabled:cursor-not-allowed text-white font-semibold text-base py-3.5 rounded-[8px] shadow-[0_2px_8px_rgba(37,99,235,0.25)] flex items-center justify-center gap-2.5 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Autenticando...</span>
              </>
            ) : (
              <>
                <span>Acessar Painel</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            type="button"
            onClick={onNavigateToApp}
            className="inline-flex items-center gap-2 text-[13px] font-semibold text-[#4B5563] hover:text-[#2563EB] transition-colors cursor-pointer"
          >
            <QrCode className="w-4 h-4" />
            <span>Voltar ao Crachá Virtual</span>
          </button>
        </div>
      </div>
    </div>
  );
}
