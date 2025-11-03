import React from 'react';
import ReactDOM from 'react-dom/client';
import './services/axiosConfig';
import App from './App';

try {
  const root = ReactDOM.createRoot(document.getElementById('root'));
  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
} catch (error) {
  console.error('Failed to render React app:', error);
  document.getElementById('root').innerHTML = `
    <div style="text-align: center; padding: 50px; color: #e74c3c;">
      <h2>Application Error</h2>
      <p>Failed to load the application. Please refresh the page.</p>
      <p style="font-size: 12px; color: #666;">${error.message}</p>
    </div>
  `;
}