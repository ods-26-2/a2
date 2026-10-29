import React from 'react';
import { ShieldCheck, Users, Settings2, QrCode, LogOut } from 'lucide-react';
import { adminLogout } from '../../services/adminApi';

export default function AdminSidebar({ activeTab, onTabChange, onNavigateToApp, onLogout }) {
  return (
    <aside className="w-[250px] shrink-0 bg-white border-r border-[#E5E7EB] flex flex-col justify-between z-20">
      <div>
        {/* Logo & Marca */}
        <div className="h-[64px] px-6 border-b border-[#E5E7EB] flex items-center gap-3">
          <div className="w-9 h-9 rounded-[8px] bg-[#2563EB] text-white flex items-center justify-center shadow-xs">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-[#111827] leading-tight">Painel Admin</h1>
            <p className="text-[11px] font-medium text-[#6B7280]">Controle de Acessos</p>
          </div>
        </div>

        {/* Menus */}
        <nav className="p-3 space-y-1">
          <button
            type="button"
            onClick={() => onTabChange('users')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-[8px] text-[13px] font-semibold transition-all cursor-pointer ${
              activeTab === 'users'
                ? 'bg-[#2563EB]/10 text-[#2563EB]'
                : 'text-[#4B5563] hover:bg-[#F9FAFB] hover:text-[#111827]'
            }`}
          >
            <Users className="w-4 h-4" />
            <span>Usuários e Acessos</span>
          </button>

          <button
            type="button"
            onClick={() => onTabChange('settings')}
            className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-[8px] text-[13px] font-semibold transition-all cursor-pointer ${
              activeTab === 'settings'
                ? 'bg-[#2563EB]/10 text-[#2563EB]'
                : 'text-[#4B5563] hover:bg-[#F9FAFB] hover:text-[#111827]'
            }`}
          >
            <Settings2 className="w-4 h-4" />
            <span>Configurações</span>
          </button>
        </nav>
      </div>

      {/* Rodapé da Sidebar */}
      <div className="p-3 border-t border-[#E5E7EB] space-y-2">
        <button
          type="button"
          onClick={onNavigateToApp}
          className="w-full flex items-center justify-center gap-2 px-3.5 py-2.5 rounded-[8px] border border-[#E5E7EB] bg-white text-[#4B5563] hover:bg-[#F9FAFB] text-[13px] font-semibold transition-all cursor-pointer shadow-2xs"
        >
          <QrCode className="w-4 h-4 text-[#2563EB]" />
          <span>Ver Crachá Virtual</span>
        </button>

        <button
          type="button"
          onClick={async () => {
            await adminLogout();
            if (onLogout) onLogout();
          }}
          className="w-full flex items-center justify-center gap-2 px-3.5 py-2 rounded-[8px] border border-red-200 bg-red-50 text-[#DC2626] hover:bg-red-100 text-[13px] font-semibold transition-all cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          <span>Encerrar Sessão</span>
        </button>
      </div>
    </aside>
  );
}
