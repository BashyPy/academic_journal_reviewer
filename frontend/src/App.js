import React, { useState, useEffect } from 'react';
import UploadForm from './components/UploadForm';
import ReviewReport from './components/ReviewReport';
import CompletionNotification from './components/CompletionNotification';
import './App.css';

function App() {
  const [submissionId, setSubmissionId] = useState(null);
  const [currentView, setCurrentView] = useState('upload');
  const [showNotification, setShowNotification] = useState(false);
  const [darkMode, setDarkMode] = useState(() => 
    localStorage.getItem('darkMode') === 'true'
  );

  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
    document.body.className = darkMode ? 'dark-mode' : 'light-mode';
  }, [darkMode]);

  return (
    <div className={`App ${darkMode ? 'dark' : 'light'}`}>
      <header className="App-header">
        <div className="header-content">
          <div>
            <h1>AARIS</h1>
            <p>Academic Agentic Review Intelligence System</p>
          </div>
          <button 
            className="theme-toggle"
            onClick={() => setDarkMode(!darkMode)}
            aria-label="Toggle theme"
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </header>
      
      <main className="App-main">
        <nav className="App-nav">
          <button 
            className={currentView === 'upload' ? 'active' : ''}
            onClick={() => setCurrentView('upload')}
          >
            📄 Upload Manuscript
          </button>
          {submissionId && (
            <button 
              className={currentView === 'report' ? 'active' : ''}
              onClick={() => setCurrentView('report')}
            >
              📋 Final Report
            </button>
          )}
        </nav>

        <div className="App-content">
          {currentView === 'upload' && (
            <UploadForm 
              onUploadSuccess={(id) => setSubmissionId(id)}
            />
          )}
          {currentView === 'report' && submissionId && (
            <ReviewReport submissionId={submissionId} />
          )}
        </div>
      </main>
      
      {submissionId && (
        <CompletionNotification 
          submissionId={submissionId}
          show={showNotification}
          onShow={() => setShowNotification(true)}
          onViewReport={() => {
            setCurrentView('report');
            setShowNotification(false);
          }}
          onClose={() => setShowNotification(false)}
        />
      )}
    </div>
  );
}

export default App;