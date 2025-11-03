import React, { useState, useEffect } from 'react';
import passkeyService from '../services/passkeyService';
import authService from '../services/authService';

const PasskeyManager = () => {
  const [passkeys, setPasskeys] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [passkeySupported, setPasskeySupported] = useState(false);

  useEffect(() => {
    const checkSupport = async () => {
      const supported = await passkeyService.isPlatformAuthenticatorAvailable();
      setPasskeySupported(supported);
      if (supported) {
        loadPasskeys();
      }
    };
    checkSupport();
  }, []);

  const loadPasskeys = async () => {
    try {
      const apiKey = authService.getApiKey();
      const keys = await passkeyService.listPasskeys(apiKey);
      setPasskeys(keys);
    } catch (err) {
      setError('Failed to load passkeys');
    }
  };

  const handleRegister = async () => {
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const apiKey = authService.getApiKey();
      await passkeyService.registerPasskey(apiKey);
      setSuccess('Biometric authentication registered successfully!');
      await loadPasskeys();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to register biometric authentication');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (credentialId) => {
    if (!window.confirm('Remove this biometric authentication method?')) return;

    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const apiKey = authService.getApiKey();
      await passkeyService.deletePasskey(credentialId, apiKey);
      setSuccess('Biometric authentication removed');
      await loadPasskeys();
    } catch (err) {
      setError('Failed to remove biometric authentication');
    } finally {
      setLoading(false);
    }
  };

  if (!passkeySupported) {
    return (
      <div className="passkey-manager">
        <h3>🔐 Biometric Authentication</h3>
        <p style={{ color: '#666' }}>
          Biometric authentication is not available on this device or browser.
        </p>
      </div>
    );
  }

  return (
    <div className="passkey-manager">
      <h3>🔐 Biometric Authentication</h3>
      <p style={{ color: '#666', marginBottom: '20px' }}>
        Use fingerprint, Face ID, or other biometric methods to sign in securely without passwords.
      </p>

      {error && <div className="error">❌ {error}</div>}
      {success && <div className="success">✅ {success}</div>}

      <button 
        onClick={handleRegister} 
        disabled={loading}
        className="auth-button"
        style={{ marginBottom: '20px' }}
      >
        {loading ? 'Registering...' : '➕ Register New Biometric'}
      </button>

      {passkeys.length > 0 && (
        <div>
          <h4>Registered Biometric Methods</h4>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {passkeys.map((passkey, index) => (
              <li 
                key={passkey.id} 
                style={{ 
                  padding: '10px',
                  border: '1px solid #ddd',
                  borderRadius: '5px',
                  marginBottom: '10px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span>
                  🔑 Biometric Method #{index + 1}
                  {passkey.transports?.length > 0 && (
                    <span style={{ fontSize: '12px', color: '#666', marginLeft: '10px' }}>
                      ({passkey.transports.join(', ')})
                    </span>
                  )}
                </span>
                <button 
                  onClick={() => handleDelete(passkey.id)}
                  disabled={loading}
                  style={{
                    background: '#f44336',
                    color: 'white',
                    border: 'none',
                    padding: '5px 15px',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {passkeys.length === 0 && (
        <p style={{ color: '#666', fontStyle: 'italic' }}>
          No biometric authentication methods registered yet.
        </p>
      )}
    </div>
  );
};

export default PasskeyManager;
