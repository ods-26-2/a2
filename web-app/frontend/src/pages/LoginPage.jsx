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
    <div className="w-full h-full flex flex-col justify-center items-center bg-[#F0F0F0] pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] px-5 select-none">
      <div className="w-full max-w-[380px] py-6 flex flex-col">
        {/* Brand */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-3">
            <QrCode className="w-11 h-11 text-[#1F2937]" strokeWidth={2.2} />
          </div>
          <h2 className="text-[22px] font-bold text-[#111827] tracking-[-0.5px]">
            Acesso
          </h2>
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
