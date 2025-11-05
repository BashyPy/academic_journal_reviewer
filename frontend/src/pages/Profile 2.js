import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import authService from '../services/authService';
import PasswordStrengthMeter from '../components/PasswordStrengthMeter';
import PasskeyManager from '../components/PasskeyManager';

const Profile = () => {
  const [profile, setProfile] = useState(null);
  const [name, setName] = useState('');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await authService.getProfile();
      setProfile(data);
      setName(data.name);
    } catch (err) {
      setError('Failed to load profile');
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await authService.updateProfile(name);
      setSuccess('Profile updated successfully');
      loadProfile();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdatePassword = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      await authService.updatePassword(currentPassword, newPassword);
      setSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setLoading(false);
    }
  };

  if (!profile) {
    return <div className="loading">Loading profile...</div>;
  }

  return (
    <div className="profile-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2 style={{ margin: 0 }}>👤 My Profile</h2>
        <button onClick={() => navigate('/')} className="btn-home" style={{ padding: '8px 16px', cursor: 'pointer' }}>🏠 Home</button>
      </div>

      <div className="profile-section">
        <h3>Account Information</h3>
        <p><strong>Email:</strong> {profile.email}</p>
        <p><strong>Role:</strong> {profile.role}</p>
        <p><strong>Status:</strong> {profile.active ? '✅ Active' : '❌ Inactive'}</p>
      </div>

      <div className="profile-section">
        <h3>Update Profile</h3>
        <form onSubmit={handleUpdateProfile}>
          <div className="form-group">
            <label>Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Updating...' : 'Update Profile'}
          </button>
        </form>
      </div>

      <div className="profile-section">
        <h3>Change Password</h3>
        <form onSubmit={handleUpdatePassword}>
          <div className="form-group">
            <label>Current Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showCurrentPassword ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                required
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword(!showCurrentPassword)}
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
                title={showCurrentPassword ? "Hide password" : "Show password"}
              >
                {showCurrentPassword ? '👁️' : '👁️🗨️'}
              </button>
            </div>
          </div>
          <div className="form-group">
            <label>New Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type={showNewPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength="8"
                style={{ paddingRight: '40px' }}
              />
              <button
                type="button"
                onClick={() => setShowNewPassword(!showNewPassword)}
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
                title={showNewPassword ? "Hide password" : "Show password"}
              >
                {showNewPassword ? '👁️' : '👁️🗨️'}
              </button>
            </div>
            <PasswordStrengthMeter password={newPassword} />
          </div>
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? 'Updating...' : 'Change Password'}
          </button>
        </form>
      </div>

      <div className="profile-section">
        <PasskeyManager />
      </div>

      <div className="profile-section danger-zone">
        <h3>⚠️ Danger Zone</h3>
        <p>Once you delete your account, there is no going back.</p>
        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="danger-button"
          >
            Delete Account
          </button>
        ) : (
          <div className="delete-confirm">
            <p><strong>Are you absolutely sure?</strong></p>
            <p>This will permanently delete your account and all associated data.</p>
            <div className="confirm-actions">
              <button onClick={async () => {
                try {
                  await authService.deleteAccount();
                  authService.logout();
                  window.location.href = '/login';
                } catch (err) {
                  setError('Failed to delete account');
                }
              }} className="danger-button">Yes, Delete My Account</button>
              <button onClick={() => setShowDeleteConfirm(false)} className="cancel-button">Cancel</button>
            </div>
          </div>
        )}
      </div>

      {error && <div className="error">❌ {error}</div>}
      {success && <div className="success">✅ {success}</div>}
    </div>
  );
};

export default Profile;
