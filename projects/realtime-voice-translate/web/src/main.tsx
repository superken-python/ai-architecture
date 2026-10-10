import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { useStore } from './state/useStore';

if (typeof window !== 'undefined') {
  (window as any).__store = useStore;
}

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
