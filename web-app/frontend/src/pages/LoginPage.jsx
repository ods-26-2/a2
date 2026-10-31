import React, { useState } from 'react';
import { QrCode, Contact, Lock, ArrowRight, Loader2 } from 'lucide-react';
import { maskCPF } from '../utils/formatters';

export default function LoginPage({ onLoginSuccess }) {
  const [cpf, setCpf] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleCpfChange = (e) => {
    setCpf(maskCPF(e.target.value));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    const cleanCpf = cpf.replace(/\D/g, '');
    if (!cleanCpf) {
      setError('Por favor, informe o CPF.');
      return;
    }

    setLoading(true);
    try {
      await onLoginSuccess(cleanCpf, password);
    } catch (err) {
      setError(err.message || 'Erro ao conectar com o servidor.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col justify-center items-center bg-[#F8FAFC] pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] px-5 select-none">
      <div className="w-full max-w-[390px] py-8 px-6 sm:px-8 bg-white border border-[#E2E8F0] rounded-[16px] shadow-[0_12px_32px_-8px_rgba(15,23,42,0.08)] flex flex-col">
        {/* Brand */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3.5">
            <div className="w-13 h-13 rounded-[12px] bg-blue-50 text-[#2563EB] flex items-center justify-center border border-blue-100 shadow-2xs">
              <QrCode className="w-7 h-7" strokeWidth={2.2} />
            </div>
          </div>
          <h2 className="text-[20px] font-bold text-[#0F172A] tracking-tight">
            Controle de Acesso
          </h2>
          <p className="text-[13px] text-[#64748B] mt-1">
            Informe suas credenciais para visualizar seu crachá
          </p>
        </div>

        {/* Error box */}
        {error && (
          <div className="bg-[#FEE2E2] border border-[#F87171] text-[#B91C1C] px-3.5 py-2.5 rounded-[8px] text-[13px] font-medium text-center mb-4 animate-in fade-in duration-200">
            {error}
          </div>
        )}

        {/* Login form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="cpf" className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
              CPF
            </label>
            <div className="relative flex items-center">
              <Contact className="absolute left-3.5 w-[18px] h-[18px] text-[#9CA3AF] pointer-events-none" />
              <input
                type="tel"
                id="cpf"
                value={cpf}
                onChange={handleCpfChange}
                placeholder="000.000.000-00"
                required
                inputMode="numeric"
                maxLength={14}
                autoComplete="username"
                className="w-full py-3.5 pl-11 pr-3.5 bg-white border border-[#D1D5DB] rounded-[8px] text-[#111827] text-base shadow-xs focus:outline-none focus:border-[#2563EB] focus:ring-3 focus:ring-[#2563EB]/15 transition-all"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
              Senha
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-[18px] h-[18px] text-[#9CA3AF] pointer-events-none" />
              <input
                type="password"
                id="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Sua senha"
                required
                autoComplete="current-password"
                className="w-full py-3.5 pl-11 pr-3.5 bg-white border border-[#D1D5DB] rounded-[8px] text-[#111827] text-base shadow-xs focus:outline-none focus:border-[#2563EB] focus:ring-3 focus:ring-[#2563EB]/15 transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] active:scale-[0.98] disabled:opacity-65 disabled:cursor-not-allowed text-white font-semibold text-base py-3.5 rounded-[8px] shadow-[0_2px_8px_rgba(37,99,235,0.25)] flex items-center justify-center gap-2.5 transition-all cursor-pointer"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Validando...</span>
              </>
            ) : (
              <>
                <span>Entrar</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
}
