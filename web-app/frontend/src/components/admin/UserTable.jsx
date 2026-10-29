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
    <div className="bg-white rounded-lg border border-[#E5E7EB] shadow-xs overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-[#F9FAFB] border-b border-[#E5E7EB] text-[12px] font-semibold text-[#4B5563] uppercase tracking-wider">
              <th className="py-3 px-5">CPF</th>
              <th className="py-3 px-5">Modalidade</th>
              <th className="py-3 px-5">Horário Permitido</th>
              <th className="py-3 px-5">Validade</th>
              <th className="py-3 px-5 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E7EB] text-[13px]">
            {users.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-10 text-center text-[#9CA3AF]">
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
                  <tr key={user.cpf} className="hover:bg-[#F9FAFB]/80 transition-colors">
                    {/* CPF */}
                    <td className="py-3.5 px-5 font-mono font-semibold text-[#111827]">
                      {formatCpfDisplay(user.cpf)}
                    </td>

                    {/* Modalidade */}
                    <td className="py-3.5 px-5 text-[#374151]">
                      {user.is_recurring ? (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[12px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-sm">
                            Recorrente
                          </span>
                          <span className="text-[12px] text-[#4B5563]">
                            {Array.isArray(user.access_days) && user.access_days.length > 0
                              ? user.access_days.map((d) => DAY_NAMES[d] || d).join(', ')
                              : 'Sem restrição de dias'}
                          </span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[12px] font-semibold text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 rounded-sm">
                            Data Fixa
                          </span>
                          <span className="text-[12px] text-[#4B5563]">
                            {Array.isArray(user.access_days) && user.access_days.length > 0
                              ? user.access_days.map((d) => DAY_NAMES[d] || d).join(', ')
                              : 'Todos os dias do período'}
                          </span>
                        </div>
                      )}
                    </td>

                    {/* Horários */}
                    <td className="py-3.5 px-5 text-[#4B5563]">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-[#9CA3AF]" />
                        <span>{hoursText}</span>
                      </div>
                    </td>

                    {/* Validade no lugar de Status */}
                    <td className="py-3.5 px-5">
                      <div className="flex flex-col gap-0.5">
                        {user.specific_date && (
                          <span className="text-[11px] text-[#6B7280]">
                            De: <strong className="text-[#374151]">{formatDisplayDate(user.specific_date)}</strong>
                          </span>
                        )}
                        {user.expiration_date ? (
                          isExpired ? (
                            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-600 bg-red-50 border border-red-200 px-2 py-0.5 rounded-sm self-start">
                              <Calendar className="w-3 h-3 text-red-500" />
                              Expirou ({formatDisplayDate(user.expiration_date)})
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-sm self-start">
                              <Calendar className="w-3 h-3 text-emerald-600" />
                              Até {formatDisplayDate(user.expiration_date)}
                            </span>
                          )
                        ) : (
                          <span className="text-[11px] text-[#9CA3AF]">
                            Sem expiração definida
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Ações */}
                    <td className="py-3.5 px-5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onEditExpiration && onEditExpiration(user)}
                          title="Configurar usuário, horários e validade"
                          className="px-2.5 py-1 text-[12px] font-semibold rounded-md border border-[#E5E7EB] text-[#374151] hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs"
                        >
                          <Settings2 className="w-3.5 h-3.5 text-[#2563EB]" />
                          <span>Configurar</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => onDeleteUser(user.cpf)}
                          title="Excluir usuário"
                          className="w-7 h-7 rounded-md border border-[#E5E7EB] text-[#9CA3AF] hover:bg-[#FEE2E2] hover:text-[#DC2626] hover:border-[#FCA5A5] flex items-center justify-center transition-all cursor-pointer"
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
