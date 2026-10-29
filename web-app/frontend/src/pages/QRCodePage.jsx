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
    <div className="w-full h-full flex flex-col bg-[#F0F0F0] pt-[env(safe-area-inset-top,0px)] pb-[env(safe-area-inset-bottom,0px)] select-none">
      {/* Top Bar */}
      <header className="h-[58px] flex items-center justify-between px-4.5 pt-4 pb-2 shrink-0">
        <div className="flex items-center gap-2 text-[14px] font-semibold text-[#374151] bg-white border border-[#E5E7EB] px-3.5 py-1.5 rounded-[20px] font-mono shadow-xs">
          <Contact className="w-4 h-4 text-[#2563EB]" />
          <span>{formatCpfDisplay(cpf)}</span>
        </div>

        <button
          type="button"
          onClick={onLogout}
          title="Sair"
          className="w-[38px] h-[38px] bg-white border border-[#E5E7EB] text-[#4B5563] hover:bg-[#FEE2E2] hover:text-[#DC2626] hover:border-[#FCA5A5] rounded-[10px] flex items-center justify-center transition-all shadow-xs cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </header>

      {/* QR Area */}
      <main className="flex-1 w-full flex items-center justify-center p-4 relative overflow-hidden">
        <div
          ref={containerRef}
          className="w-[min(80vw,80vh)] aspect-square bg-white border-[16px] border-white rounded-[20px] shadow-[0_10px_35px_rgba(0,0,0,0.1)] flex items-center justify-center overflow-hidden"
        >
          <canvas
            ref={canvasRef}
            className="w-full h-full block object-contain [image-rendering:pixelated]"
          />
        </div>

        {/* Loading Overlay */}
        {loadingPayload && (
          <div className="absolute inset-0 bg-[#F0F0F0]/85 z-10 flex flex-col items-center justify-center gap-2.5 text-[13px] font-medium text-[#374151] animate-in fade-in duration-150">
            <Loader2 className="w-6 h-6 text-[#2563EB] animate-spin" />
            <span>Atualizando payload...</span>
          </div>
        )}
      </main>

      {/* Bottom Bar */}
      <footer className="min-h-[64px] flex flex-col items-center justify-center px-4 pb-4 pt-2 gap-2 shrink-0">
        {payload?.startDate && payload?.endDate ? (
          <div className="flex items-center gap-2 text-[13px] font-semibold text-[#374151] bg-white border border-[#E5E7EB] px-3.5 py-1.5 rounded-[20px] shadow-xs">
            <Clock className="w-4 h-4 text-[#10B981]" />
            <span>{formatValidity(payload.startDate, payload.endDate)}</span>
          </div>
        ) : null}

        {payload?.isRecurring && payload?.expirationDate ? (
          <div className="flex items-center gap-1.5 text-[12px] font-medium text-[#4B5563] bg-white border border-[#E5E7EB] px-3 py-1 rounded-[16px] shadow-xs animate-in fade-in duration-200">
            <Calendar className="w-3.5 h-3.5 text-[#2563EB]" />
            <span>
              Validade da recorrência: <strong className="text-[#1F2937]">{formatDisplayDate(payload.expirationDate)}</strong>
            </span>
          </div>
        ) : null}

        {!payload?.isRecurring ? (
          <div className="flex items-center gap-1.5 text-[12px] font-medium text-purple-700 bg-purple-50 border border-purple-200 px-3 py-1 rounded-[16px] shadow-xs animate-in fade-in duration-200">
            <Calendar className="w-3.5 h-3.5 text-purple-600" />
            <span>Acesso por Data Fixa</span>
          </div>
        ) : null}
      </footer>
    </div>
  );
}
