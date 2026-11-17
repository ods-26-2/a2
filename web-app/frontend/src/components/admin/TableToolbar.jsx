import React from 'react';
import { Search, Plus, Filter } from 'lucide-react';

export default function TableToolbar({
  searchTerm,
  onSearchChange,
  statusFilter,
  onFilterChange,
  onOpenNewUser,
}) {
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 flex-1 max-w-[560px]">
        {/* Campo de Busca */}
        <div className="relative flex-1 flex items-center">
          <Search className="absolute left-3.5 w-4 h-4 text-[#94A3B8] pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Buscar por CPF..."
            className="w-full h-10 pl-10 pr-3.5 bg-white border border-[#CBD5E1] rounded-[8px] text-[13px] text-[#0F172A] placeholder:text-[#94A3B8] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] shadow-2xs transition-all"
          />
        </div>

        {/* Filtro Dropdown */}
        <div className="relative flex items-center">
          <Filter className="absolute left-3 w-3.5 h-3.5 text-[#94A3B8] pointer-events-none" />
          <select
            value={statusFilter}
            onChange={(e) => onFilterChange(e.target.value)}
            className="h-10 pl-8.5 pr-8 bg-white border border-[#CBD5E1] rounded-[8px] text-[13px] font-medium text-[#334155] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB] shadow-2xs transition-all cursor-pointer appearance-none"
          >
            <option value="all">Todas as Modalidades</option>
            <option value="recurring">Recorrentes (Semanal)</option>
            <option value="specific">Data Fixa</option>
            <option value="valid">Dentro da Validade</option>
            <option value="expired">Validade Expirada</option>
          </select>
          <div className="absolute right-3 pointer-events-none text-[#94A3B8] text-xs">▼</div>
        </div>
      </div>

      {/* Botão Novo Usuário */}
      <button
        type="button"
        onClick={onOpenNewUser}
        className="h-10 px-4 bg-[#2563EB] hover:bg-[#1D4ED8] active:bg-[#1E40AF] text-white rounded-[8px] text-[13px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-all cursor-pointer shrink-0"
      >
        <Plus className="w-4 h-4" />
        <span>Novo Usuário</span>
      </button>
    </div>
  );
}
