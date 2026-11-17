import React, { useState, useEffect } from 'react';
import { Copy, Check, RefreshCw, Power, Loader2 } from 'lucide-react';
import { fetchApiKey, regenerateApiKey, toggleApiKey } from '../../services/adminApi';

export default function ApiKeysCard() {
  const [apiKey, setApiKey] = useState(null);
  const [active, setActive] = useState(false);
  const [createdAt, setCreatedAt] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);
  const [showKey, setShowKey] = useState(false);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchApiKey();
      setApiKey(data.key);
      setActive(Boolean(data.active));
      setCreatedAt(data.created_at);
    } catch (err) {
      setError(err.message || 'Erro ao carregar chave de API');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRegenerate = async () => {
    if (!window.confirm('Regenerar a chave de API? A chave anterior deixará de funcionar.')) return;
    setSaving(true);
    setError('');
    try {
      const data = await regenerateApiKey();
      setApiKey(data.key);
      setActive(Boolean(data.active));
      setCreatedAt(new Date().toISOString());
    } catch (err) {
      setError(err.message || 'Erro ao regenerar chave');
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async () => {
    setSaving(true);
    setError('');
    try {
      const data = await toggleApiKey(!active);
      setActive(Boolean(data.active));
    } catch (err) {
      setError(err.message || 'Erro ao alterar status da chave');
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = async () => {
    if (!apiKey) return;
    try {
      await navigator.clipboard.writeText(apiKey);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Não foi possível copiar a chave.');
    }
  };

  return (
    <div className="w-full bg-white rounded-[8px] border border-[#E5E7EB] shadow-xs p-6 space-y-6">
      <div>
        <h3 className="text-base font-bold text-[#111827]">Chave de API</h3>
        <p className="text-[13px] text-[#6B7280]">
          Permite acessar endpoints externos (criação/edição de usuários) via header <code>X-API-Key</code>.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-[#FEE2E2] border border-[#F87171] text-[#B91C1C] rounded-[8px] text-[13px] font-medium">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-[13px] text-[#6B7280]">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span>Carregando chave...</span>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-[#F9FAFB] border border-[#D1D5DB] rounded-[8px] px-3 py-2 font-mono text-[13px] text-[#111827] break-all">
              {apiKey ? (showKey ? apiKey : '•'.repeat(Math.min(apiKey.length, 40))) : 'Nenhuma chave gerada'}
            </div>
            {apiKey && (
              <>
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="px-3 py-2 rounded-[8px] border border-[#D1D5DB] text-[#4B5563] hover:bg-[#F9FAFB] text-[13px] font-medium cursor-pointer"
                >
                  {showKey ? 'Ocultar' : 'Mostrar'}
                </button>
                <button
                  type="button"
                  onClick={handleCopy}
                  className="px-3 py-2 rounded-[8px] border border-[#D1D5DB] text-[#4B5563] hover:bg-[#F9FAFB] text-[13px] font-medium cursor-pointer flex items-center gap-1.5"
                >
                  {copied ? <Check className="w-4 h-4 text-[#10B981]" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copiado' : 'Copiar'}
                </button>
              </>
            )}
          </div>

          {createdAt && (
            <p className="text-[11px] text-[#6B7280]">
              Criada em: {String(createdAt).replace('T', ' ').slice(0, 19)}
            </p>
          )}

          <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[#E5E7EB]">
            <button
              type="button"
              onClick={handleToggle}
              disabled={saving || !apiKey}
              className={`px-4 py-2 rounded-[8px] text-[13px] font-semibold flex items-center gap-2 transition-all cursor-pointer border ${
                active
                  ? 'bg-emerald-50 border-emerald-300 text-emerald-700 hover:bg-emerald-100'
                  : 'bg-[#F9FAFB] border-[#D1D5DB] text-[#4B5563] hover:bg-[#F3F4F6]'
              } disabled:opacity-65`}
            >
              <Power className="w-4 h-4" />
              {active ? 'Ativa' : 'Inativa'}
            </button>

            <button
              type="button"
              onClick={handleRegenerate}
              disabled={saving}
              className="px-4 py-2 bg-[#2563EB] hover:bg-[#1D4ED8] text-white rounded-[8px] text-[13px] font-semibold flex items-center gap-2 shadow-xs transition-all cursor-pointer disabled:opacity-65"
            >
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
              <span>{apiKey ? 'Regenerar' : 'Gerar Chave'}</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
