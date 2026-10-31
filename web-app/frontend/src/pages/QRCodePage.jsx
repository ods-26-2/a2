import React, { useEffect, useRef } from 'react';
import QRCode from 'qrcode';
import { Contact, LogOut, Clock, Loader2, Calendar } from 'lucide-react';
import { formatCpfDisplay, formatValidity, formatDisplayDate, hexToBytes } from '../utils/formatters';

export default function QRCodePage({ cpf, payload, loadingPayload, onLogout }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  useEffect(() => {
    if (!payload?.data || !canvasRef.current) return;

    try {
      const rawBytes = hexToBytes(payload.data);
      const containerWidth = containerRef.current?.clientWidth || 320;
      // Define a largura em pixels de acordo com o container para manter a nitidez perfeita
      const targetWidth = Math.max(containerWidth, 320);

      QRCode.toCanvas(
        canvasRef.current,
        [{ data: rawBytes, mode: 'byte' }],
        {
          errorCorrectionLevel: 'L',
          version: 1,
          margin: 1,
          width: targetWidth,
          color: {
            dark: '#000000',
            light: '#FFFFFF',
          },
        },
        (error) => {
          if (error) {
            console.error('Erro ao renderizar QR code:', error);
          }
        }
      );
    } catch (err) {
      console.error('Falha na geração do QR Code:', err);
    }
  }, [payload]);

  return (
    <div className="w-full h-full flex flex-col bg-[#F8FAFC] pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] select-none">
      {/* Top Bar */}
      <header className="h-[60px] flex items-center justify-between px-5 pt-3 pb-2 shrink-0">
        <div className="flex items-center gap-2 text-[13px] font-semibold text-[#334155] bg-white border border-[#E2E8F0] px-3.5 py-1.5 rounded-full font-mono shadow-xs">
          <Contact className="w-4 h-4 text-[#2563EB]" />
          <span>{formatCpfDisplay(cpf)}</span>
        </div>

        <button
          type="button"
          onClick={onLogout}
          title="Sair"
          className="w-[38px] h-[38px] bg-white border border-[#E2E8F0] text-[#64748B] hover:bg-red-50 hover:text-red-600 hover:border-red-200 rounded-[10px] flex items-center justify-center transition-all shadow-xs cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </header>

      {/* QR Area */}
      <main className="flex-1 w-full flex items-center justify-center p-4 relative overflow-hidden">
        <div
          ref={containerRef}
          className="w-[min(80vw,80vh)] aspect-square bg-white border-[16px] border-white rounded-[24px] shadow-[0_12px_40px_-10px_rgba(15,23,42,0.12)] flex items-center justify-center overflow-hidden"
        >
          <canvas
            ref={canvasRef}
            className="w-full h-full block object-contain [image-rendering:pixelated]"
          />
        </div>

        {/* Loading Overlay */}
        {loadingPayload && (
          <div className="absolute inset-0 bg-white/80 backdrop-blur-xs z-10 flex flex-col items-center justify-center gap-2.5 text-[13px] font-medium text-[#334155] animate-in fade-in duration-150">
            <Loader2 className="w-6 h-6 text-[#2563EB] animate-spin" />
            <span>Atualizando payload...</span>
          </div>
        )}
      </main>

      {/* Bottom Bar */}
      <footer className="min-h-[64px] flex flex-col items-center justify-center px-4 pb-4 pt-2 gap-2 shrink-0">
        {payload?.startDate && payload?.endDate ? (
          <div className="flex items-center gap-2 text-[13px] font-semibold text-[#334155] bg-white border border-[#E2E8F0] px-3.5 py-1.5 rounded-full shadow-xs">
            <Clock className="w-4 h-4 text-emerald-600" />
            <span>{formatValidity(payload.startDate, payload.endDate)}</span>
          </div>
        ) : null}

        {payload?.isRecurring && payload?.expirationDate ? (
          <div className="flex items-center gap-1.5 text-[12px] font-medium text-[#475569] bg-white border border-[#E2E8F0] px-3.5 py-1 rounded-full shadow-xs animate-in fade-in duration-200">
            <Calendar className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>
              Validade da recorrência: <strong className="text-[#0F172A]">{formatDisplayDate(payload.expirationDate)}</strong>
            </span>
          </div>
        ) : null}

        {!payload?.isRecurring ? (
          <div className="flex items-center gap-1.5 text-[12px] font-semibold text-purple-700 bg-purple-50 border border-purple-200 px-3.5 py-1 rounded-full shadow-xs animate-in fade-in duration-200">
            <Calendar className="w-3.5 h-3.5 text-purple-600" />
            <span>Acesso por Data Fixa</span>
          </div>
        ) : null}
      </footer>
    </div>
  );
}
