import React from 'react';
import { Calendar, Repeat, CalendarDays } from 'lucide-react';
import DaySelector from './DaySelector';

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
                ? 'Nenhum dia selecionado: máscara de dias = 0.'
                : 'Dias selecionados geram máscara com bit 1 nas posições correspondentes.'}
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
                    Data de Término *
                  </label>
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
          </div>
        </div>
      )}
    </div>
  );
}
