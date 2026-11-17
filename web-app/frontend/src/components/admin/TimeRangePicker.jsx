import React from 'react';
import { Clock } from 'lucide-react';

export default function TimeRangePicker({
  startHour,
  setStartHour,
  endHour,
  setEndHour,
}) {
  return (
    <div className="bg-[#FAFBFD] p-4 rounded-[10px] border border-[#E5E7EB] space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-[13px] font-semibold text-[#1F2937]">
          Horário Permitido nas Catracas
        </label>
        <span className="text-[11px] font-medium text-[#2563EB] bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-sm">
          {startHour && endHour ? `${startHour} às ${endHour}` : 'Horário livre'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
        <div>
          <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
            Horário de Entrada
          </label>
          <div className="relative flex items-center">
            <Clock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
            <input
              type="time"
              value={startHour}
              onChange={(e) => setStartHour(e.target.value)}
              className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-md text-sm font-mono text-[#111827] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
            />
          </div>
        </div>

        <div>
          <label className="block text-[12px] font-medium text-[#4B5563] mb-1.5">
            Horário Limite de Saída
          </label>
          <div className="relative flex items-center">
            <Clock className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
            <input
              type="time"
              value={endHour}
              onChange={(e) => setEndHour(e.target.value)}
              className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-md text-sm font-mono text-[#111827] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
