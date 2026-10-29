import React from 'react';
import { Search, Plus } from 'lucide-react';

export default function TableToolbar({
  searchTerm,
  onSearchChange,
  statusFilter,
  onFilterChange,
  onOpenNewUser,
}) {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
      <div className="flex items-center gap-3 flex-1 max-w-[500px]">
        <div className="relative flex-1 flex items-center">
          <Search className="absolute left-3 w-4 h-4 text-[#9CA3AF] pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Buscar por CPF..."
            className="w-full py-2 pl-9 pr-3 bg-white border border-[#D1D5DB] rounded-[8px] text-[14px] text-[#111827] focus:outline-none focus:border-[#2563EB] focus:ring-3 focus:ring-[#2563EB]/15"
          />
        </div>

        <select
          value={statusFilter}
          onChange={(e) => onFilterChange(e.target.value)}
          className="py-2 px-3 bg-white border border-[#D1D5DB] rounded-[8px] text-[13px] font-medium text-[#374151] focus:outline-none focus:border-[#2563EB] cursor-pointer"
        >
          <option value="all">Todas as Modalidades</option>
          <option value="recurring">Recorrentes (Semanal)</option>
          <option value="specific">Data Fixa</option>
          <option value="valid">Dentro da Validade</option>
          <option value="expired">Validade Expirada</option>
        </select>
      </div>

      <button
        type="button"
        onClick={onOpenNewUser}
        className="px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] text-white rounded-[8px] text-[13px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer shrink-0"
      >
        <Plus className="w-4 h-4" />
        <span>Novo Usuário</span>
      </button>
    </div>
  );
}
