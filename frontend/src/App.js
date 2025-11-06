import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import VerifyEmail from './pages/VerifyEmail';
import ForgotPassword from './pages/ForgotPassword';
import Profile from './pages/Profile';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import AdminDashboard from './pages/AdminDashboard';
import AuthorDashboard from './pages/AuthorDashboard';
import EditorDashboard from './pages/EditorDashboard';
import ReviewerDashboard from './pages/ReviewerDashboard';
import UploadManuscript from './pages/UploadManuscript';
import ReviewPage from './pages/ReviewPage';
import './App.css';



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
        <Route path="/admin-dashboard" element={<ProtectedRoute><AdminDashboard /></ProtectedRoute>} />
        <Route path="/super-admin" element={<ProtectedRoute><SuperAdminDashboard /></ProtectedRoute>} />
        <Route path="/upload" element={<ProtectedRoute><UploadManuscript /></ProtectedRoute>} />
        <Route path="/review/:submissionId" element={<ProtectedRoute><ReviewPage /></ProtectedRoute>} />
        <Route path="/" element={<Navigate to="/author-dashboard" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
