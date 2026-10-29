import React, { useState } from 'react';
import { Lock, Check, Loader2, Eye, EyeOff } from 'lucide-react';
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
    <div className="w-full bg-white rounded-[8px] border border-[#E5E7EB] shadow-xs p-6 space-y-6">
      <div>
        <h3 className="text-base font-bold text-[#111827]">Alterar Senha do Administrador</h3>
        <p className="text-[13px] text-[#6B7280]">
          Atualize a senha de acesso ao painel administrativo.
        </p>
      </div>

      {feedback && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-[#065F46] rounded-[8px] text-[13px] font-medium flex items-center gap-2 animate-in fade-in">
          <Check className="w-4 h-4 text-[#10B981]" />
          <span>{feedback}</span>
        </div>
      )}

      {error && (
        <div className="p-3 bg-[#FEE2E2] border border-[#F87171] text-[#B91C1C] rounded-[8px] text-[13px] font-medium">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4 max-w-[480px]">
        <div>
          <label className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
            Senha Atual
          </label>
          <div className="relative flex items-center">
            <Lock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
            <input
              type={showCurrent ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              className="w-full py-2 pl-9 pr-10 bg-white border border-[#D1D5DB] rounded-[8px] text-sm text-[#111827] focus:outline-none focus:border-[#2563EB]"
            />
            <button
              type="button"
              onClick={() => setShowCurrent((v) => !v)}
              className="absolute right-3 text-[#9CA3AF] hover:text-[#4B5563]"
            >
              {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
            Nova Senha
          </label>
          <div className="relative flex items-center">
            <Lock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
            <input
              type={showNew ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              className="w-full py-2 pl-9 pr-10 bg-white border border-[#D1D5DB] rounded-[8px] text-sm text-[#111827] focus:outline-none focus:border-[#2563EB]"
            />
            <button
              type="button"
              onClick={() => setShowNew((v) => !v)}
              className="absolute right-3 text-[#9CA3AF] hover:text-[#4B5563]"
            >
              {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <div>
          <label className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
            Confirmar Nova Senha
          </label>
          <div className="relative flex items-center">
            <Lock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
            <input
              type={showNew ? 'text' : 'password'}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[8px] text-sm text-[#111827] focus:outline-none focus:border-[#2563EB]"
            />
          </div>
        </div>

        <div className="pt-2">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] text-sm font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer disabled:opacity-65"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            <span>Alterar Senha</span>
          </button>
        </div>
      </form>
    </div>
  );
}