import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Users,
  LogIn,
  LogOut,
  Clock,
  RefreshCw,
  Search,
  Activity,
  CheckCircle2,
  Building2,
} from 'lucide-react';
import { fetchDashboardMetrics, fetchDashboardPresence } from '../../services/adminApi';
import { formatCpfDisplay } from '../../utils/formatters';

export default function DashboardView() {
  const [metrics, setMetrics] = useState({
    people_count: 0,
    total_entries_today: 0,
    total_exits_today: 0,
    last_event_at: null,
  });
  const [presenceData, setPresenceData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filterInside, setFilterInside] = useState('all'); // 'all', 'inside', 'outside'
  const [searchTerm, setSearchTerm] = useState('');

  const loadDashboardData = useCallback(async (isSilent = false) => {
    try {
      if (!isSilent) setRefreshing(true);
      const [m, p] = await Promise.all([
        fetchDashboardMetrics().catch(() => null),
        fetchDashboardPresence().catch(() => ({ items: [] })),
      ]);

      if (m) setMetrics(m);
      if (p && Array.isArray(p.items)) setPresenceData(p.items);
    } catch (err) {
      console.error('Erro ao carregar dados do dashboard:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Atualização em tempo real sempre ligada (a cada 4 segundos)
  useEffect(() => {
    const interval = setInterval(() => {
      loadDashboardData(true);
    }, 4000);
    return () => clearInterval(interval);
  }, [loadDashboardData]);

  const filteredPresence = useMemo(() => {
    return presenceData.filter((item) => {
      // Filtro de status
      if (filterInside === 'inside' && !item.is_inside) return false;
      if (filterInside === 'outside' && item.is_inside) return false;

      // Filtro de busca por CPF
      if (searchTerm.trim()) {
        const cleanSearch = searchTerm.replace(/\D/g, '');
        const strCpf = String(item.cpf || '');
        if (cleanSearch && !strCpf.includes(cleanSearch)) {
          return false;
        }
      }
      return true;
    });
  }, [presenceData, filterInside, searchTerm]);

  const formatDateTime = (dtStr) => {
    if (!dtStr) return '-';
    try {
      const parts = dtStr.split(' ');
      if (parts.length === 2) {
        const [d, t] = parts;
        const [y, m, day] = d.split('-');
        return `${day}/${m}/${y} ${t.substring(0, 5)}`;
      }
      return dtStr;
    } catch {
      return dtStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Topo / Barra de Ferramentas de Atualização */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white border border-[#E5E7EB] rounded-[10px] p-4 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-[8px] bg-[#2563EB]/10 text-[#2563EB] flex items-center justify-center">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-[#111827]">Visão Geral de Ocupação</h2>
            <p className="text-[12px] text-[#6B7280]">
              Métricas em tempo real atualizadas a cada evento nas catracas
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-auto justify-end">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span>
            Tempo Real Ativo
          </span>

          <button
            type="button"
            onClick={() => loadDashboardData(false)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-[#1E293B] bg-[#F1F5F9] hover:bg-[#E2E8F0] border border-[#CBD5E1] rounded-[6px] transition-all cursor-pointer disabled:opacity-50"
            title="Atualizar dados agora"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#2563EB]' : ''}`} />
            <span>Atualizar</span>
          </button>
        </div>
      </div>

      {/* Grid de Cards KPI */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Pessoas no Prédio */}
        <div className="bg-white border border-[#E5E7EB] rounded-[10px] p-5 shadow-xs relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-bold uppercase tracking-wider text-[#6B7280]">
              Ocupação Atual
            </span>
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#10B981] animate-pulse"></span>
              Ao vivo
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#111827] tracking-tight">
              {metrics.people_count ?? 0}
            </span>
            <span className="text-xs font-medium text-[#6B7280]">pessoas no prédio</span>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F3F4F6] flex items-center justify-between text-xs text-[#6B7280]">
            <div className="flex items-center gap-1.5">
              <Users className="w-4 h-4 text-[#2563EB]" />
              <span>Contador interno</span>
            </div>
            <span className="font-semibold text-[#111827]">
              {presenceData.filter((p) => p.is_inside).length} identificados
            </span>
          </div>
        </div>

        {/* Card 2: Entradas Hoje */}
        <div className="bg-white border border-[#E5E7EB] rounded-[10px] p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-bold uppercase tracking-wider text-[#6B7280]">
              Entradas Hoje
            </span>
            <div className="w-7 h-7 rounded-[6px] bg-[#10B981]/10 text-[#10B981] flex items-center justify-center">
              <LogIn className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#111827] tracking-tight">
              {metrics.total_entries_today ?? 0}
            </span>
            <span className="text-xs font-medium text-[#6B7280]">giros confirmados</span>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F3F4F6] text-xs text-[#6B7280] flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" />
            <span>Fluxo de entrada do dia</span>
          </div>
        </div>

        {/* Card 3: Saídas Hoje */}
        <div className="bg-white border border-[#E5E7EB] rounded-[10px] p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-bold uppercase tracking-wider text-[#6B7280]">
              Saídas Hoje
            </span>
            <div className="w-7 h-7 rounded-[6px] bg-[#F59E0B]/10 text-[#F59E0B] flex items-center justify-center">
              <LogOut className="w-4 h-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#111827] tracking-tight">
              {metrics.total_exits_today ?? 0}
            </span>
            <span className="text-xs font-medium text-[#6B7280]">giros confirmados</span>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F3F4F6] text-xs text-[#6B7280] flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-[#F59E0B]" />
            <span>Fluxo de saída do dia</span>
          </div>
        </div>

        {/* Card 4: Último Acesso */}
        <div className="bg-white border border-[#E5E7EB] rounded-[10px] p-5 shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[12px] font-bold uppercase tracking-wider text-[#6B7280]">
              Última Atividade
            </span>
            <div className="w-7 h-7 rounded-[6px] bg-[#8B5CF6]/10 text-[#8B5CF6] flex items-center justify-center">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="text-xl font-bold text-[#111827] tracking-tight">
              {metrics.last_event_at ? formatDateTime(metrics.last_event_at) : 'Nenhum registro'}
            </span>
            <span className="text-xs text-[#6B7280] mt-0.5">catraca mais recente</span>
          </div>
          <div className="mt-3 pt-3 border-t border-[#F3F4F6] text-xs text-[#6B7280]">
            <span>Registro via telemetria</span>
          </div>
        </div>
      </div>

      {/* Tabela de Presença (Quem está e não está na parte interna) */}
      <div className="bg-white border border-[#E5E7EB] rounded-[10px] shadow-xs overflow-hidden">
        {/* Header da Tabela com Filtros e Busca */}
        <div className="p-4 sm:p-5 border-b border-[#E5E7EB] flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-[#111827]">Controle de Presença (Interno / Externo)</h3>
            <p className="text-xs text-[#6B7280]">
              Tabela indexada por CPF com o status de localização imediata
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            {/* Filtros de Status */}
            <div className="inline-flex rounded-[8px] border border-[#E5E7EB] p-0.5 bg-[#F9FAFB]">
              <button
                type="button"
                onClick={() => setFilterInside('all')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-[6px] transition-all cursor-pointer ${
                  filterInside === 'all'
                    ? 'bg-white text-[#111827] shadow-2xs'
                    : 'text-[#6B7280] hover:text-[#111827]'
                }`}
              >
                Todos ({presenceData.length})
              </button>
              <button
                type="button"
                onClick={() => setFilterInside('inside')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-[6px] transition-all cursor-pointer ${
                  filterInside === 'inside'
                    ? 'bg-white text-[#10B981] shadow-2xs font-bold'
                    : 'text-[#6B7280] hover:text-[#10B981]'
                }`}
              >
                No Prédio ({presenceData.filter((p) => p.is_inside).length})
              </button>
              <button
                type="button"
                onClick={() => setFilterInside('outside')}
                className={`px-3 py-1.5 text-xs font-semibold rounded-[6px] transition-all cursor-pointer ${
                  filterInside === 'outside'
                    ? 'bg-white text-[#6B7280] shadow-2xs font-bold'
                    : 'text-[#6B7280] hover:text-[#111827]'
                }`}
              >
                Fora ({presenceData.filter((p) => !p.is_inside).length})
              </button>
            </div>

            {/* Input de Busca */}
            <div className="relative min-w-[200px]">
              <Search className="w-4 h-4 text-[#9CA3AF] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Buscar por CPF..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-white border border-[#E5E7EB] rounded-[8px] focus:outline-none focus:border-[#2563EB] focus:ring-1 focus:ring-[#2563EB]"
              />
            </div>
          </div>
        </div>

        {/* Tabela */}
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB] text-[#4B5563] font-semibold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">CPF</th>
                <th className="py-3 px-4">Localização Atual</th>
                <th className="py-3 px-4">Último Sentido</th>
                <th className="py-3 px-4">Dispositivo / Catraca</th>
                <th className="py-3 px-4">Última Entrada</th>
                <th className="py-3 px-4">Última Saída</th>
                <th className="py-3 px-4">Atualizado Em</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F3F4F6]">
              {loading ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-[#6B7280]">
                    Carregando dados de presença...
                  </td>
                </tr>
              ) : filteredPresence.length === 0 ? (
                <tr>
                  <td colSpan="7" className="py-8 text-center text-[#9CA3AF]">
                    {searchTerm
                      ? 'Nenhum usuário encontrado para esta busca.'
                      : 'Nenhum registro de acesso recebido até o momento.'}
                  </td>
                </tr>
              ) : (
                filteredPresence.map((row) => (
                  <tr key={row.cpf} className="hover:bg-[#F9FAFB] transition-colors">
                    {/* CPF */}
                    <td className="py-3 px-4 font-mono font-bold text-[#111827]">
                      {formatCpfDisplay(row.cpf)}
                    </td>

                    {/* Status de Presença */}
                    <td className="py-3 px-4">
                      {row.is_inside ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#ECFDF5] text-[#10B981] border border-[#A7F3D0]">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#10B981]"></span>
                          No Prédio (Interno)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-[#F1F5F9] text-[#64748B] border border-[#E2E8F0]">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#94A3B8]"></span>
                          Fora do Prédio
                        </span>
                      )}
                    </td>

                    {/* Último Sentido */}
                    <td className="py-3 px-4">
                      {row.last_direction === 'entrada' ? (
                        <span className="inline-flex items-center gap-1 text-[#10B981] font-semibold">
                          <LogIn className="w-3.5 h-3.5" />
                          <span>Entrada</span>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[#F59E0B] font-semibold">
                          <LogOut className="w-3.5 h-3.5" />
                          <span>Saída</span>
                        </span>
                      )}
                    </td>

                    {/* Catraca */}
                    <td className="py-3 px-4 text-[#4B5563] font-mono">
                      {row.last_device_id || '-'}
                    </td>

                    {/* Última Entrada */}
                    <td className="py-3 px-4 text-[#4B5563]">
                      {formatDateTime(row.last_entry_at)}
                    </td>

                    {/* Última Saída */}
                    <td className="py-3 px-4 text-[#4B5563]">
                      {formatDateTime(row.last_exit_at)}
                    </td>

                    {/* Atualizado Em */}
                    <td className="py-3 px-4 text-[#6B7280]">
                      {formatDateTime(row.updated_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

