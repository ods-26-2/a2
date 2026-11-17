import React from 'react';
import { Calendar, Clock, Trash2, Settings2 } from 'lucide-react';
import { formatCpfDisplay, formatDisplayDate, isDateExpired } from '../../utils/formatters';

const DAY_NAMES = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];

export default function UserTable({
  users,
  onDeleteUser,
  onEditExpiration,
}) {
  return (
    <div className="bg-white rounded-[10px] border border-[#E2E8F0] shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0] text-[11px] font-semibold text-[#64748B] uppercase tracking-wider">
              <th className="py-3.5 px-5">CPF</th>
              <th className="py-3.5 px-5">Modalidade</th>
              <th className="py-3.5 px-5">Horário Permitido</th>
              <th className="py-3.5 px-5">Validade</th>
              <th className="py-3.5 px-5 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F1F5F9] text-[13px]">
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-12 text-center text-[#94A3B8]">
                  Nenhum usuário encontrado com os filtros selecionados.
                </td>
              </tr>
            ) : (
              users.map((user) => {
                const hours = user.access_hours || {};
                const hoursText =
                  hours.start && hours.end ? `${hours.start} às ${hours.end}` : 'Livre';

                const isExpired = user.expiration_date
                  ? isDateExpired(user.expiration_date)
                  : false;

                return (
                  <tr key={user.cpf} className="hover:bg-[#F8FAFC] transition-colors">
                    {/* CPF */}
                    <td className="py-3.5 px-5 font-mono font-semibold text-[#0F172A]">
                      {formatCpfDisplay(user.cpf)}
                    </td>

                    {/* Modalidade */}
                    <td className="py-3.5 px-5 text-[#334155]">
                      {user.is_recurring ? (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[11px] font-semibold text-[#1D4ED8] bg-blue-50 border border-blue-200/80 px-2 py-0.5 rounded-[4px]">
                            Recorrente
                          </span>
                          <span className="text-[12px] text-[#64748B]">
                            {Array.isArray(user.access_days) && user.access_days.length > 0
                              ? user.access_days.map((d) => DAY_NAMES[d] || d).join(', ')
                              : 'Sem restrição de dias'}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[11px] font-semibold text-[#7E22CE] bg-purple-50 border border-purple-200/80 px-2 py-0.5 rounded-[4px]">
                            Data Fixa
                          </span>
                          <span className="text-[12px] text-[#64748B]">
                            {Array.isArray(user.access_days) && user.access_days.length > 0
                              ? user.access_days.map((d) => DAY_NAMES[d] || d).join(', ')
                              : 'Todos os dias do período'}
                          </span>
                        </div>
                      )}
                    </td>

                    {/* Horários */}
                    <td className="py-3.5 px-5 text-[#475569]">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-[#94A3B8]" />
                        <span>{hoursText}</span>
                      </div>
                    </td>

                    {/* Validade */}
                    <td className="py-3.5 px-5">
                      <div className="flex flex-col gap-0.5">
                        {user.specific_date && (
                          <span className="text-[11px] text-[#64748B]">
                            De: <strong className="text-[#334155]">{formatDisplayDate(user.specific_date)}</strong>
                          </span>
                        )}
                        {user.expiration_date ? (
                          isExpired ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-[4px] self-start">
                              <Calendar className="w-3 h-3 text-red-500" />
                              Expirou ({formatDisplayDate(user.expiration_date)})
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-[4px] self-start">
                              <Calendar className="w-3 h-3 text-emerald-600" />
                              Até {formatDisplayDate(user.expiration_date)}
                            </span>
                          )
                        ) : (
                          <span className="text-[11px] text-[#94A3B8]">
                            Sem expiração definida
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Ações */}
                    <td className="py-3.5 px-5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => onEditExpiration && onEditExpiration(user)}
                          title="Configurar usuário, horários e validade"
                          className="h-8 px-2.5 text-[12px] font-medium rounded-[6px] border border-[#CBD5E1] bg-white text-[#334155] hover:bg-[#F8FAFC] hover:text-[#0F172A] hover:border-[#94A3B8] transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs"
                        >
                          <Settings2 className="w-3.5 h-3.5 text-[#64748B]" />
                          <span>Configurar</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => onDeleteUser(user.cpf)}
                          title="Excluir usuário"
                          className="w-8 h-8 rounded-[6px] border border-[#CBD5E1] bg-white text-[#94A3B8] hover:bg-red-50 hover:text-red-600 hover:border-red-200 flex items-center justify-center transition-all cursor-pointer shadow-2xs"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
