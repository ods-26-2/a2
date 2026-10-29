import React from 'react';
import { Calendar, Repeat, CalendarDays } from 'lucide-react';
import DaySelector from './DaySelector';

const RECURRING_PRESETS = [
  { label: '+30 dias', days: 30 },
  { label: '+90 dias', days: 90 },
  { label: '+6 meses', days: 180 },
  { label: '+1 ano', days: 365 },
];

export default function AccessModeSelector({
  isRecurring,
  setIsRecurring,
  accessDays,
  toggleDay,
  expirationDate,
  setExpirationDate,
  specificDate,
  setSpecificDate,
}) {
  const setRecurringPreset = (days) => {
    const base = specificDate ? new Date(`${specificDate}T00:00:00`) : new Date();
    base.setDate(base.getDate() + days);
    const pad = (n) => String(n).padStart(2, '0');
    setExpirationDate(`${base.getFullYear()}-${pad(base.getMonth() + 1)}-${pad(base.getDate())}`);
  };

  const setFixedPresetDays = (days) => {
    const base = specificDate ? new Date(`${specificDate}T00:00:00`) : new Date();
    base.setDate(base.getDate() + days);
    const pad = (n) => String(n).padStart(2, '0');
    setExpirationDate(`${base.getFullYear()}-${pad(base.getMonth() + 1)}-${pad(base.getDate())}`);
  };

  return (
    <div className="space-y-4">
      {/* Seletor de Modalidade - Abas Segmentadas */}
      <div>
        <label className="block text-[13px] font-semibold text-[#1F2937] mb-2">
          Modalidade de Acesso
        </label>
        <div className="grid grid-cols-2 p-1 bg-[#F3F4F6] rounded-[8px] border border-[#E5E7EB] gap-1">
          <button
            type="button"
            onClick={() => setIsRecurring(true)}
            className={`py-2 px-3 text-[13px] font-medium rounded-[6px] flex items-center justify-center gap-2 transition-all cursor-pointer ${
              isRecurring
                ? 'bg-white text-[#1D4ED8] shadow-xs font-semibold'
                : 'text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            <Repeat className="w-4 h-4 text-[#2563EB]" />
            <span>Recorrente (Semanal)</span>
          </button>
          <button
            type="button"
            onClick={() => setIsRecurring(false)}
            className={`py-2 px-3 text-[13px] font-medium rounded-[6px] flex items-center justify-center gap-2 transition-all cursor-pointer ${
              !isRecurring
                ? 'bg-white text-[#7E22CE] shadow-xs font-semibold'
                : 'text-[#6B7280] hover:text-[#111827]'
            }`}
          >
            <CalendarDays className="w-4 h-4 text-[#9333EA]" />
            <span>Data Fixa / Impressão</span>
          </button>
        </div>
      </div>

      {/* Conteúdo da Modalidade */}
      {isRecurring ? (
        <div className="p-4.5 rounded-[10px] bg-[#FAFBFD] border border-[#E5E7EB] space-y-4">
          {/* Dias de Acesso */}
          <div className="space-y-2">
            <DaySelector selectedDays={accessDays} onToggleDay={toggleDay} />
          </div>

          {/* Validade e Ativação da Recorrência */}
          <div className="pt-3.5 border-t border-[#E5E7EB] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
                  Data de Início (Ativação)
                </label>
                <div className="relative flex items-center">
                  <Calendar className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="date"
                    value={specificDate}
                    onChange={(e) => setSpecificDate(e.target.value)}
                    className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[6px] text-sm text-[#111827] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[12px] font-medium text-[#4B5563]">
                    Validade da Recorrência
                  </label>
                  <span className="text-[11px] text-[#9CA3AF]">Opcional</span>
                </div>
                <div className="relative flex items-center">
                  <Calendar className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="date"
                    value={expirationDate}
                    onChange={(e) => setExpirationDate(e.target.value)}
                    className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[6px] text-sm text-[#111827] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span className="text-[11px] font-medium text-[#6B7280]">Atalhos de validade:</span>
              {RECURRING_PRESETS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => setRecurringPreset(p.days)}
                  className="px-2.5 py-1 text-[11px] font-medium rounded-[5px] border border-[#D1D5DB] bg-white text-[#374151] hover:border-[#2563EB] hover:text-[#2563EB] hover:bg-blue-50/50 transition-all cursor-pointer"
                >
                  {p.label}
                </button>
              ))}
              {expirationDate && (
                <button
                  type="button"
                  onClick={() => setExpirationDate('')}
                  className="px-2.5 py-1 text-[11px] font-medium rounded-[5px] border border-[#E5E7EB] bg-white text-red-600 hover:bg-red-50 transition-all cursor-pointer"
                >
                  Limpar
                </button>
              )}
            </div>

            <p className="text-[11px] text-[#6B7280]">
              Após esta data de validade, os QR codes recorrentes deixarão de autorizar o acesso.
            </p>
          </div>
        </div>
      ) : (
        /* Data Fixa / Impressão */
        <div className="p-4.5 rounded-[10px] bg-[#FAFBFD] border border-[#E5E7EB] space-y-4">
          {/* Dias de Acesso Opcionais para Impressão Fixa */}
          <div className="space-y-2">
            <DaySelector selectedDays={accessDays} onToggleDay={toggleDay} />
            <p className="text-[11px] text-[#6B7280]">
              {accessDays.length === 0
                ? 'Nenhum dia restrito: acesso autorizado em todos os dias do período.'
                : 'Acesso restrito apenas aos dias da semana selecionados acima.'}
            </p>
          </div>

          <div className="pt-3.5 border-t border-[#E5E7EB] space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
                  Data de Início *
                </label>
                <div className="relative flex items-center">
                  <Calendar className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="date"
                    value={specificDate}
                    onChange={(e) => setSpecificDate(e.target.value)}
                    required={!isRecurring}
                    className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[6px] text-sm text-[#111827] focus:outline-none focus:border-[#7E22CE] focus:ring-1 focus:ring-[#7E22CE]"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-[12px] font-medium text-[#4B5563]">
                    Data de Término
                  </label>
                  <span className="text-[11px] text-[#9CA3AF]">Opcional</span>
                </div>
                <div className="relative flex items-center">
                  <Calendar className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
                  <input
                    type="date"
                    value={expirationDate}
                    onChange={(e) => setExpirationDate(e.target.value)}
                    className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[6px] text-sm text-[#111827] focus:outline-none focus:border-[#7E22CE] focus:ring-1 focus:ring-[#7E22CE]"
                  />
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-medium text-[#6B7280]">Extensão do período:</span>
              {[
                { label: '+1 dia', days: 1 },
                { label: '+3 dias', days: 3 },
                { label: '+1 semana', days: 7 },
                { label: '+30 dias', days: 30 },
              ].map((p) => (
                <button
                  key={p.label}
                  type="button"
                  onClick={() => setFixedPresetDays(p.days)}
                  className="px-2.5 py-1 text-[11px] font-medium rounded-[5px] border border-[#D1D5DB] bg-white text-[#374151] hover:border-[#9333EA] hover:text-[#7E22CE] hover:bg-purple-50/50 transition-all cursor-pointer"
                >
                  {p.label}
                </button>
              ))}
              {expirationDate && (
                <button
                  type="button"
                  onClick={() => setExpirationDate('')}
                  className="px-2.5 py-1 text-[11px] font-medium rounded-[5px] border border-[#E5E7EB] bg-white text-red-600 hover:bg-red-50 transition-all cursor-pointer"
                >
                  Limpar
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}