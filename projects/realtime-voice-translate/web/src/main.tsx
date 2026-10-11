import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { useStore } from './state/useStore';
import { rvtClient } from './net/ws_client';

if (typeof window !== 'undefined') {
  (window as any).__store = useStore;
  (window as any).__rvtClient = rvtClient;
}

class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught application error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '24px', color: '#f87171', background: '#121212', minHeight: '100vh', fontFamily: 'system-ui, sans-serif', boxSizing: 'border-box' }}>
          <h2 style={{ marginTop: 0 }}>⚠️ Đã xảy ra lỗi giao diện</h2>
          <pre style={{ background: '#18181b', padding: '12px', borderRadius: '8px', border: '1px solid #334155', overflowX: 'auto', color: '#fecaca', fontSize: '13px' }}>
            {this.state.error?.message || String(this.state.error)}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: '16px', padding: '10px 20px', borderRadius: '8px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600 }}
          >
            🔄 Tải lại trang
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
