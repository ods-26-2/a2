import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary capturou erro:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full h-full flex items-center justify-center bg-[#F0F0F0] p-6">
          <div className="bg-white max-w-[500px] w-full p-6 rounded-[12px] border border-[#F87171] shadow-md text-center">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-red-100 text-[#DC2626] flex items-center justify-center">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-lg font-bold text-[#111827] mb-2">Ocorreu um erro na interface</h2>
            <p className="text-sm text-[#4B5563] mb-4">
              {this.state.error?.message || 'Erro inesperado durante a renderização.'}
            </p>
            <button
              type="button"
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-4 py-2 bg-[#2563EB] text-white text-sm font-semibold rounded-[8px] hover:bg-[#1D4ED8] inline-flex items-center gap-2 cursor-pointer"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Recarregar Página</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
