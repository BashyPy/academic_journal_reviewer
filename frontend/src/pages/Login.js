import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import passkeyService from '../services/passkeyService';

const Login = () => {
  const [emailOrUsername, setEmailOrUsername] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passkeyAvailable, setPasskeyAvailable] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const checkPasskey = async () => {
      const available = await passkeyService.isPlatformAuthenticatorAvailable();
      setPasskeyAvailable(available);
    };
    checkPasskey();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login(emailOrUsername, password, rememberMe);
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setError('');
    setLoading(true);

    try {
      const result = await passkeyService.authenticateWithPasskey();
      await authService.loginWithPasskey(
        result.api_key,
        result.access_token,
        result.user,
        rememberMe
      );
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Biometric login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>🔐 Login to AARIS</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Email or Username</label>
            <input
              type="text"
              value={emailOrUsername}
              onChange={(e) => setEmailOrUsername(e.target.value)}
              required
              placeholder="email@example.com or username"
            />
          </div>
          <div className="form-group">
            <label>Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter password"
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '10px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '18px'
                }}
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? '👁️' : '👁️🗨️'}
              </button>
            </div>
          </div>
          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
              />
              Remember me for 30 days
            </label>
          </div>
          {error && <div className="error">❌ {error}</div>}
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>
        {passkeyAvailable && (
          <div style={{ margin: '20px 0', textAlign: 'center' }}>
            <div style={{ borderTop: '1px solid #ddd', margin: '20px 0', position: 'relative' }}>
              <span style={{ 
                position: 'absolute', 
                top: '-12px', 
                left: '50%', 
                transform: 'translateX(-50%)',
                background: 'white',
                padding: '0 10px',
                color: '#666'
              }}>OR</span>
            </div>
            <button 
              onClick={handlePasskeyLogin} 
              disabled={loading}
              className="auth-button"
              style={{ background: '#4CAF50' }}
            >
              🔐 {loading ? 'Authenticating...' : 'Login with Biometric'}
            </button>
            <p style={{ fontSize: '12px', color: '#666', marginTop: '10px' }}>
              Use fingerprint, Face ID, or other biometric authentication
            </p>
          </div>
        )}
        <div className="auth-links">
          <a href="/register">Don't have an account? Register</a>
          <a href="/forgot-password">Forgot password?</a>
        </div>
      </div>
    </div>
  );
};

export default Login;
