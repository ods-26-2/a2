import React from 'react';
import { RefreshCw } from 'lucide-react';

export default function AdminHeader({ activeTab, loading, onRefresh, adminUser }) {
  const username = adminUser?.username || 'admin';

  return (
    <header className="h-[64px] bg-white border-b border-[#E5E7EB] px-8 flex items-center justify-between shrink-0">
      <div>
        <h2 className="text-base font-bold text-[#111827]">
          {activeTab === 'users' ? 'Gestão de Usuários e Permissões' : 'Configurações do Sistema'}
        </h2>
        <p className="text-[12px] text-[#6B7280]">
          {activeTab === 'users'
            ? 'Gerencie credenciais e regras de validação para catracas e leitores'
            : 'Parâmetros de geração de payloads e lotes'}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onRefresh}
          title="Atualizar dados"
          disabled={loading}
          className="w-9 h-9 rounded-[8px] border border-[#E5E7EB] text-[#4B5563] hover:bg-[#F9FAFB] flex items-center justify-center transition-all cursor-pointer shadow-2xs"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-[#2563EB]' : ''}`} />
        </button>

        <div className="flex items-center gap-2.5 pl-3 border-l border-[#E5E7EB]">
          <div className="w-8 h-8 rounded-full bg-[#2563EB]/15 text-[#2563EB] flex items-center justify-center text-xs font-bold uppercase">
            {username.slice(0, 2)}
          </div>
          <div className="flex flex-col text-left">
            <span className="text-[13px] font-semibold text-[#374151] leading-tight">
              {username}
            </span>
            <span className="text-[11px] font-medium text-[#10B981] leading-tight flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>
              Autenticado
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
