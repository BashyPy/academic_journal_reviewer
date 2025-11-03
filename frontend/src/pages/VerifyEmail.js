import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import authService from '../services/authService';

const VerifyEmail = () => {
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const email = location.state?.email || '';

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.verifyEmail(email, otp);
      setSuccess('Email verified! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setLoading(true);

    try {
      await authService.resendVerification(email);
      setSuccess('Verification code resent to your email');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to resend code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>✉️ Verify Your Email</h2>
        <p>Enter the 6-digit code sent to {email}</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Verification Code</label>
            <input
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              required
              maxLength="6"
              placeholder="123456"
              style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem' }}
            />
          </div>
          {error && <div className="error">❌ {error}</div>}
          {success && <div className="success">✅ {success}</div>}
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Verifying...' : 'Verify Email'}
          </button>
        </form>
        <div className="auth-links">
          <button onClick={handleResend} disabled={loading} className="link-button">
            Resend verification code
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;
