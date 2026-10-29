import React, { useState, useEffect } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { updateAdminConfig } from '../../services/adminApi';

export default function ApiConfigCard({ initialBatchSize, onConfigUpdated }) {
  const [batchSizeInput, setBatchSizeInput] = useState(initialBatchSize || 10);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState('');

  useEffect(() => {
    if (initialBatchSize) setBatchSizeInput(initialBatchSize);
  }, [initialBatchSize]);

  const handleSaveConfig = async (e) => {
    e.preventDefault();
    setSaving(true);
    setFeedback('');
    try {
      await updateAdminConfig(batchSizeInput);
      setFeedback('Configurações salvas com sucesso!');
      setTimeout(() => setFeedback(''), 3000);
      if (onConfigUpdated) onConfigUpdated();
    } catch (err) {
      alert(err.message || 'Erro ao salvar configuração');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-[8px] border border-[#E5E7EB] shadow-xs p-6 space-y-6">
      <div>
        <h3 className="text-base font-bold text-[#111827]">Configurações da API</h3>
        <p className="text-[13px] text-[#6B7280]">
          Ajuste parâmetros globais do backend e da geração de lotes de payloads.
        </p>
      </div>

      {feedback && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-[#065F46] rounded-[8px] text-[13px] font-medium flex items-center gap-2 animate-in fade-in">
          <Check className="w-4 h-4 text-[#10B981]" />
          <span>{feedback}</span>
        </div>
      )}

      <form onSubmit={handleSaveConfig} className="space-y-4">
        <div>
          <label className="block text-[13px] font-medium text-[#4B5563] mb-1.5">
            Tamanho do Lote de Payloads (Batch Size)
          </label>
          <div className="flex items-center gap-3">
            <input
              type="number"
              min="1"
              max="100"
              value={batchSizeInput}
              onChange={(e) => setBatchSizeInput(e.target.value)}
              required
              className="w-32 py-2 px-3 bg-white border border-[#D1D5DB] rounded-[8px] text-[15px] font-semibold text-[#111827] focus:outline-none focus:border-[#2563EB]"
            />
            <span className="text-[13px] text-[#6B7280]">
              registros retornados pela rota <code>/get-payloads</code>
            </span>
          </div>
        </div>

        <div className="pt-4 border-t border-[#E5E7EB] flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] text-sm font-semibold shadow-xs flex items-center gap-2 transition-all cursor-pointer"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Salvando...</span>
              </>
            ) : (
              'Salvar Configurações'
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
