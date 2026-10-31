import React from 'react';

export default function AdminHeader({ activeTab }) {
  return (
    <header className="h-[64px] bg-white border-b border-[#E5E7EB] px-8 flex items-center justify-between shrink-0">
      <div>
        <h2 className="text-base font-bold text-[#111827]">
          {activeTab === 'users' ? 'Gestão de Usuários e Permissões' : activeTab === 'docs' ? 'Documentação da API' : 'Configurações do Sistema'}
        </h2>
        <p className="text-[12px] text-[#6B7280]">
          {activeTab === 'users'
            ? 'Gerencie credenciais e regras de validação para catracas e leitores'
            : activeTab === 'docs'
            ? 'Referência dos endpoints e uso da chave de API'
            : 'Parâmetros de geração de payloads e lotes'}
        </p>
      </div>
    </header>
  );
}
