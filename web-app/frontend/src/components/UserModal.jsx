import { useState } from 'react';
import { X, Contact, Lock, Loader2, ShieldCheck, UserCheck } from 'lucide-react';
import { maskCPF } from '../utils/formatters';
import AccessModeSelector from './admin/AccessModeSelector';
import TimeRangePicker from './admin/TimeRangePicker';

const getTodayString = () => {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

export default function UserModal({ initialUser = null, onClose, onSaved }) {
  const isEditing = Boolean(initialUser);
  const [cpf, setCpf] = useState(initialUser?.cpf ? maskCPF(initialUser.cpf) : '');
  const [password, setPassword] = useState('');
  const [isRecurring, setIsRecurring] = useState(initialUser?.is_recurring !== undefined ? Boolean(initialUser.is_recurring) : true);
  const [specificDate, setSpecificDate] = useState(
    initialUser?.specific_date ? String(initialUser.specific_date).slice(0, 10) : getTodayString()
  );
  const [expirationDate, setExpirationDate] = useState(
    initialUser?.expiration_date ? String(initialUser.expiration_date).slice(0, 10) : ''
  );
  const [accessDays, setAccessDays] = useState(Array.isArray(initialUser?.access_days) ? initialUser.access_days : [0, 1, 2, 3, 4]);
  const [startHour, setStartHour] = useState(initialUser?.access_hours?.start || '08:00');
  const [endHour, setEndHour] = useState(initialUser?.access_hours?.end || '18:00');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const toggleDay = (dayId) => {
    setAccessDays((prev) => (prev.includes(dayId) ? prev.filter((d) => d !== dayId) : [...prev, dayId].sort()));
  };

  const handleModeChange = (recurring) => {
    setIsRecurring(recurring);
    if (!recurring) {
      setAccessDays([]);
    } else if (accessDays.length === 0) {
      setAccessDays([0, 1, 2, 3, 4]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const cleanCpf = cpf.replace(/\D/g, '');
    if (cleanCpf.length !== 11) {
      setError('O CPF deve conter exatamente 11 dígitos.');
      return;
    }
    if (!isEditing && !password) {
      setError('Por favor, informe uma senha para o novo usuário.');
      return;
    }
    if (!isRecurring && !specificDate) {
      setError('Por favor, informe a Data de Início.');
      return;
    }
    if (expirationDate && specificDate && expirationDate < specificDate) {
      setError('A Data de Término / Validade não pode ser anterior à Data de Início.');
      return;
    }
    if (isRecurring && accessDays.length === 0) {
      setError('Selecione ao menos um dia da semana para o acesso recorrente.');
      return;
    }

    setSaving(true);
    try {
      await onSaved({
        cpf: parseInt(cleanCpf, 10),
        password: password || undefined,
        is_recurring: isRecurring,
        specific_date: specificDate || null,
        expiration_date: expirationDate || null,
        access_days: accessDays,
        access_hours: { start: startHour, end: endHour },
      });
      onClose();
    } catch (err) {
      setError(err.message || 'Falha ao salvar usuário');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#0F172A]/50 backdrop-blur-xs p-4 sm:p-6 animate-in fade-in duration-200">
      <div className="bg-white rounded-[14px] border border-[#E2E8F0] shadow-[0_24px_48px_-12px_rgba(15,23,42,0.18)] w-full max-w-[620px] overflow-hidden flex flex-col max-h-[92vh] transition-all">
        {/* Header Elegante & Alinhado */}
        <div className="flex items-center justify-between px-6 py-4.5 border-b border-[#E2E8F0] bg-linear-to-b from-[#FAFBFD] to-white">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-[10px] flex items-center justify-center border ${isEditing ? 'bg-amber-50 text-amber-600 border-amber-200' : 'bg-blue-50 text-blue-600 border-blue-200'}`}>
              {isEditing ? <UserCheck className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
            </div>
            <div>
              <h3 className="text-base font-bold text-[#0F172A]">
                {isEditing ? 'Configurar Credenciais & Acesso' : 'Cadastrar Novo Usuário'}
              </h3>
              <p className="text-[12px] text-[#64748B] mt-0.5">
                {isEditing ? `Gerenciando regras de catraca para CPF ${maskCPF(initialUser.cpf)}` : 'Defina os parâmetros de permissão e autenticação para as catracas'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg border border-[#E2E8F0] text-[#64748B] hover:bg-[#FEE2E2] hover:text-[#DC2626] hover:border-[#FCA5A5] flex items-center justify-center transition-all cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Formulário com Espaçamento Consistente */}
        <form onSubmit={handleSubmit} className="overflow-y-auto px-6 py-5.5 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2.5 rounded-lg text-[13px] font-medium flex items-center justify-center">
              {error}
            </div>
          )}

          {/* Grid de Identificação e Credenciais */}
          <div className="bg-[#FAFBFD] p-4 rounded-[10px] border border-[#E5E7EB] space-y-3">
            <h4 className="text-[13px] font-semibold text-[#1F2937]">Identificação & Senha</h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
                  CPF {isEditing ? '(Identificador fixo)' : '*'}
                </label>
                <div className="relative flex items-center">
                  <Contact className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="tel"
                    value={cpf}
                    onChange={(e) => !isEditing && setCpf(maskCPF(e.target.value))}
                    placeholder="000.000.000-00"
                    required
                    disabled={isEditing}
                    maxLength={14}
                    className={`w-full py-2 pl-9 pr-3 border rounded-md text-sm font-mono transition-all ${
                      isEditing
                        ? 'bg-[#F1F5F9] text-[#64748B] border-[#CBD5E1] cursor-not-allowed'
                        : 'bg-white text-[#0F172A] border-[#D1D5DB] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]'
                    }`}
                  />
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
                  {isEditing ? 'Nova Senha (deixe em branco p/ manter)' : 'Senha de Acesso *'}
                </label>
                <div className="relative flex items-center">
                  <Lock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="text"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={isEditing ? '••••••••' : 'Defina a senha'}
                    required={!isEditing}
                    className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-md text-sm text-[#0F172A] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Modalidade de Liberação */}
          <AccessModeSelector
            isRecurring={isRecurring}
            setIsRecurring={handleModeChange}
            accessDays={accessDays}
            toggleDay={toggleDay}
            expirationDate={expirationDate}
            setExpirationDate={setExpirationDate}
            specificDate={specificDate}
            setSpecificDate={setSpecificDate}
          />

          {/* Faixa de Horários */}
          <TimeRangePicker
            startHour={startHour}
            setStartHour={setStartHour}
            endHour={endHour}
            setEndHour={setEndHour}
          />

          {/* Rodapé com Ações Alinhadas */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#E2E8F0]">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="px-4 py-2 rounded-md border border-[#D1D5DB] text-sm font-medium text-[#475569] hover:bg-[#F8FAFC] transition-all cursor-pointer"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-5 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] text-white rounded-md text-sm font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Salvando...</span>
                </>
              ) : isEditing ? (
                'Salvar Alterações'
              ) : (
                'Criar Usuário'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
