import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import UploadForm from './components/UploadForm';
import ReviewReport from './components/ReviewReport';
import CompletionNotification from './components/CompletionNotification';
import ProtectedRoute from './components/ProtectedRoute';
import SessionTimeout from './components/SessionTimeout';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import Profile from './pages/Profile';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import AuthorDashboard from './pages/AuthorDashboard';
import EditorDashboard from './pages/EditorDashboard';
import ReviewerDashboard from './pages/ReviewerDashboard';
import authService from './services/authService';
import './App.css';

function MainApp() {
  const [submissionId, setSubmissionId] = useState(null);
  const [currentView, setCurrentView] = useState('upload');
  const [showNotification, setShowNotification] = useState(false);
  const [darkMode, setDarkMode] = useState(() => 
    localStorage.getItem('darkMode') === 'true'
  );
  const [user, setUser] = useState(authService.getUser());
  const navigate = useNavigate();

  useEffect(() => {
    localStorage.setItem('darkMode', darkMode);
    document.body.className = darkMode ? 'dark-mode' : 'light-mode';
  }, [darkMode]);

  const handleLogout = () => {
    authService.logout();
    setUser(null);
    navigate('/login');
  };

  return (
    <div className={`App ${darkMode ? 'dark' : 'light'}`}>
      <header className="App-header">
        <div className="header-content">
          <div>
            <h1>AARIS</h1>
            <p>Academic Agentic Review Intelligence System</p>
          </div>
          <div className="header-actions">
            {user && (
              <div className="user-menu">
                <span>👤 {user.name}</span>
                <button onClick={() => navigate('/author-dashboard')} className="dashboard-btn">📊 Dashboard</button>
                {user.role === 'reviewer' && (
                  <button onClick={() => navigate('/reviewer-dashboard')} className="reviewer-btn">📝 Reviews</button>
                )}
                {user.role === 'editor' && (
                  <button onClick={() => navigate('/editor-dashboard')} className="editor-btn">📝 Editor</button>
                )}
                {user.role === 'super_admin' && (
                  <button onClick={() => navigate('/super-admin')} className="admin-btn">🛡️ Admin</button>
                )}
                <button onClick={() => navigate('/profile')} className="profile-btn">Profile</button>
                <button onClick={handleLogout} className="logout-btn">Logout</button>
              </div>
            )}
            <button 
              className="theme-toggle"
              onClick={() => setDarkMode(!darkMode)}
              aria-label="Toggle theme"
            >
              {darkMode ? '☀️' : '🌙'}
            </button>
          </div>
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
      <SessionTimeout />
    </div>
  );
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/verify-email" element={<VerifyEmail />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/author-dashboard" element={<ProtectedRoute><AuthorDashboard /></ProtectedRoute>} />
        <Route path="/reviewer-dashboard" element={<ProtectedRoute><ReviewerDashboard /></ProtectedRoute>} />
        <Route path="/editor-dashboard" element={<ProtectedRoute><EditorDashboard /></ProtectedRoute>} />
        <Route path="/super-admin" element={<ProtectedRoute><SuperAdminDashboard /></ProtectedRoute>} />
        <Route path="/" element={<ProtectedRoute><MainApp /></ProtectedRoute>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;