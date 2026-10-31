import React, { useState } from 'react';
import { Lock, Check, Loader2, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { changeAdminPassword } from '../../services/adminApi';

export default function AdminPasswordCard() {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setFeedback('');

    if (!currentPassword) {
      setError('Informe a senha atual.');
      return;
    }
    if (!newPassword || newPassword.length < 4) {
      setError('A nova senha deve ter pelo menos 4 caracteres.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('A confirmação não coincide com a nova senha.');
      return;
    }

    setSaving(true);
    try {
      await changeAdminPassword(currentPassword, newPassword);
      setFeedback('Senha alterada com sucesso!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setFeedback(''), 3000);
    } catch (err) {
      setError(err.message || 'Erro ao alterar a senha');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-[10px] border border-[#E2E8F0] shadow-xs p-6 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-[8px] bg-blue-50 text-[#2563EB] flex items-center justify-center shrink-0">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-base font-bold text-[#0F172A]">Alterar Senha do Administrador</h3>
          <p className="text-[13px] text-[#64748B]">
            Atualize as credenciais de acesso ao painel administrativo.
          </p>
        </div>
      </div>

      {feedback && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-[#065F46] rounded-[8px] text-[13px] font-medium flex items-center gap-2 animate-in fade-in">
          <Check className="w-4 h-4 text-[#10B981]" />
          <span>{feedback}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-[8px] text-[13px] font-medium">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Grid com os 3 inputs em colunas proporcionais para preencher a largura de forma harmoniosa */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-[12px] font-medium text-[#475569] mb-1.5">
              Senha Atual *
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 w-4 h-4 text-[#94A3B8] pointer-events-none" />
              <input
                type={showCurrent ? 'text' : 'password'}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Senha atual"
                required
                className="w-full h-10 pl-9 pr-10 bg-white border border-[#CBD5E1] rounded-[8px] text-sm text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-all"
              />
              <button
                type="button"
                onClick={() => setShowCurrent((v) => !v)}
                tabIndex={-1}
                className="absolute right-3 text-[#94A3B8] hover:text-[#475569] cursor-pointer"
              >
                {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#475569] mb-1.5">
              Nova Senha *
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 w-4 h-4 text-[#94A3B8] pointer-events-none" />
              <input
                type={showNew ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Mínimo 4 caracteres"
                required
                className="w-full h-10 pl-9 pr-10 bg-white border border-[#CBD5E1] rounded-[8px] text-sm text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-all"
              />
              <button
                type="button"
                onClick={() => setShowNew((v) => !v)}
                tabIndex={-1}
                className="absolute right-3 text-[#94A3B8] hover:text-[#475569] cursor-pointer"
              >
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#475569] mb-1.5">
              Confirmar Nova Senha *
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3 w-4 h-4 text-[#94A3B8] pointer-events-none" />
              <input
                type={showNew ? 'text' : 'password'}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Repita a nova senha"
                required
                className="w-full h-10 pl-9 pr-3 bg-white border border-[#CBD5E1] rounded-[8px] text-sm text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] transition-all"
              />
            </div>
          </div>
        </div>

        <div className="pt-2 flex justify-start">
          <button
            type="submit"
            disabled={saving}
            className="h-10 px-5 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] text-white rounded-[8px] text-[13px] font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer disabled:opacity-65"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            <span>Salvar Nova Senha</span>
          </button>
        </div>
      </form>
    </div>
  );
}
