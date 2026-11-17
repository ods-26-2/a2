import { useId } from 'react';

const DAYS = [
  { id: 0, label: 'Seg', name: 'Segunda' },
  { id: 1, label: 'Ter', name: 'Terça' },
  { id: 2, label: 'Qua', name: 'Quarta' },
  { id: 3, label: 'Qui', name: 'Quinta' },
  { id: 4, label: 'Sex', name: 'Sexta' },
  { id: 5, label: 'Sáb', name: 'Sábado' },
  { id: 6, label: 'Dom', name: 'Domingo' },
];

export default function DaySelector({ selectedDays, onToggleDay }) {
  const baseId = useId();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-[13px] font-medium text-[#374151]">
          Dias da Semana Autorizados
        </label>
        <span className="text-[11px] font-medium text-[#6B7280]">
          {selectedDays.length === 7
            ? 'Todos os dias'
            : selectedDays.length === 5 && !selectedDays.includes(5) && !selectedDays.includes(6)
            ? 'Seg a Sex'
            : `${selectedDays.length} selecionado(s)`}
        </span>
      </div>

      <div className="grid grid-cols-7 gap-1.5 sm:gap-2">
        {DAYS.map((day) => {
          const selected = selectedDays.includes(day.id);
          return (
            <button
              key={`${baseId}-${day.id}`}
              type="button"
              onClick={() => onToggleDay(day.id)}
              title={day.name}
              className={`h-10 rounded-[8px] text-[13px] font-semibold border flex items-center justify-center transition-all cursor-pointer select-none ${
                selected
                  ? 'bg-[#2563EB] border-[#2563EB] text-white shadow-xs scale-[1.02]'
                  : 'bg-white border-[#D1D5DB] text-[#4B5563] hover:border-[#9CA3AF] hover:bg-[#F9FAFB]'
              }`}
            >
              {day.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
