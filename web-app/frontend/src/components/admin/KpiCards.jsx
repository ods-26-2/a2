import React from 'react';
import { Users, CheckCircle2, XCircle, Sliders } from 'lucide-react';

export default function KpiCards({ stats, usersCount, configBatchSize }) {
  const totalUsers = stats?.total_users ?? usersCount;
  const activeUsers = stats?.active_users ?? 0;
  const inactiveUsers = stats?.inactive_users ?? 0;
  const batchSize = stats?.payload_batch_size ?? configBatchSize ?? 10;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-white p-4.5 rounded-[8px] border border-[#E5E7EB] shadow-xs flex items-center justify-between">
        <div>
          <p className="text-[12px] font-medium text-[#6B7280]">Total de Usuários</p>
          <h3 className="text-2xl font-bold text-[#111827] mt-0.5">{totalUsers}</h3>
        </div>
        <div className="w-10 h-10 rounded-[8px] bg-blue-50 text-[#2563EB] flex items-center justify-center">
          <Users className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-white p-4.5 rounded-[8px] border border-[#E5E7EB] shadow-xs flex items-center justify-between">
        <div>
          <p className="text-[12px] font-medium text-[#6B7280]">Acessos Ativos</p>
          <h3 className="text-2xl font-bold text-[#10B981] mt-0.5">{activeUsers}</h3>
        </div>
        <div className="w-10 h-10 rounded-[8px] bg-emerald-50 text-[#10B981] flex items-center justify-center">
          <CheckCircle2 className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-white p-4.5 rounded-[8px] border border-[#E5E7EB] shadow-xs flex items-center justify-between">
        <div>
          <p className="text-[12px] font-medium text-[#6B7280]">Acessos Bloqueados</p>
          <h3 className="text-2xl font-bold text-[#EF4444] mt-0.5">{inactiveUsers}</h3>
        </div>
        <div className="w-10 h-10 rounded-[8px] bg-red-50 text-[#EF4444] flex items-center justify-center">
          <XCircle className="w-5 h-5" />
        </div>
      </div>

      <div className="bg-white p-4.5 rounded-[8px] border border-[#E5E7EB] shadow-xs flex items-center justify-between">
        <div>
          <p className="text-[12px] font-medium text-[#6B7280]">Tamanho do Lote</p>
          <h3 className="text-2xl font-bold text-[#111827] mt-0.5">{batchSize}</h3>
        </div>
        <div className="w-10 h-10 rounded-[8px] bg-purple-50 text-purple-600 flex items-center justify-center">
          <Sliders className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
