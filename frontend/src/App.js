import React, { useState } from 'react';
import UploadForm from './components/UploadForm';
import ReviewStatus from './components/ReviewStatus';
import ReviewReport from './components/ReviewReport';
import './App.css';

function App() {
  const [submissionId, setSubmissionId] = useState(null);
  const [currentView, setCurrentView] = useState('upload');

  return (
    <div className="App">
      <header className="App-header">
        <h1>AARIS</h1>
        <p>Academic Agentic Review Intelligence System</p>
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
            <>
              <button 
                className={currentView === 'status' ? 'active' : ''}
                onClick={() => setCurrentView('status')}
              >
                📊 Review Status
              </button>
              <button 
                className={currentView === 'report' ? 'active' : ''}
                onClick={() => setCurrentView('report')}
              >
                📋 Final Report
              </button>
            </>
          )}
        </nav>

        <div className="App-content">
          {currentView === 'upload' && (
            <UploadForm 
              onUploadSuccess={(id) => {
                setSubmissionId(id);
                setCurrentView('status');
              }}
            />
          )}
          {currentView === 'status' && submissionId && (
            <ReviewStatus submissionId={submissionId} />
          )}
          {currentView === 'report' && submissionId && (
            <ReviewReport submissionId={submissionId} />
          )}
        </div>
      </main>
    </div>
  );
}

export default App;