import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import authService from '../services/authService';
import UploadForm from '../components/UploadForm';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [userStats, setUserStats] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [showCreateKey, setShowCreateKey] = useState(false);
  const [newKey, setNewKey] = useState({
    name: '',
    role: 'author',
    expires_days: 365
  });
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetPasswordData, setResetPasswordData] = useState({
    identifier: '',
    new_password: ''
  });
  const [showResetPasswordField, setShowResetPasswordField] = useState(false);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      const [statsRes, usersRes, submissionsRes, logsRes, analyticsRes] = await Promise.all([
        axios.get('/api/v1/admin-dashboard/stats'),
        axios.get('/api/v1/admin-dashboard/users?limit=10'),
        axios.get('/api/v1/admin-dashboard/submissions?limit=10'),
        axios.get('/api/v1/admin-dashboard/audit-logs?limit=20'),
        axios.get('/api/v1/admin-dashboard/analytics/submissions?days=30'),
      ]);

      setStats(statsRes.data);
      setUsers(usersRes.data.users);
      setSubmissions(submissionsRes.data.submissions);
      setAuditLogs(logsRes.data.logs);
      setAnalytics(analyticsRes.data);
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      alert('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const loadApiKeys = async () => {
    try {
      const res = await axios.get('/api/v1/admin-dashboard/api-keys');
      setApiKeys(res.data.api_keys);
    } catch (error) {
      console.error('Failed to load API keys:', error);
    }
  };

  const loadRecentActivity = async () => {
    try {
      const res = await axios.get('/api/v1/admin-dashboard/recent-activity?limit=20');
      setRecentActivity(res.data.recent_activity);
    } catch (error) {
      console.error('Failed to load recent activity:', error);
    }
  };

  const loadUserStats = async () => {
    try {
      const res = await axios.get('/api/v1/admin-dashboard/user-statistics');
      setUserStats(res.data.user_statistics);
    } catch (error) {
      console.error('Failed to load user statistics:', error);
    }
  };

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await axios.patch(`/api/v1/admin-dashboard/users/${userId}/status`, {
        is_active: !isActive
      });
      alert(`User ${!isActive ? 'activated' : 'deactivated'} successfully`);
      loadDashboardData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update user status');
    }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    if (!window.confirm(`Reset password for ${resetPasswordData.identifier}?`)) return;

    try {
      await axios.post('/api/v1/admin/users/reset-password', resetPasswordData);
      alert('Password reset successfully');
      setShowResetPassword(false);
      setResetPasswordData({ identifier: '', new_password: '' });
      setShowResetPasswordField(false);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  const createApiKey = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/v1/admin-dashboard/api-keys', newKey);
      alert(`API Key created successfully!\n\nKey: ${res.data.key}\n\nSave this key securely - it won't be shown again!`);
      setShowCreateKey(false);
      setNewKey({ name: '', role: 'author', expires_days: 365 });
      loadApiKeys();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create API key');
    }
  };

  const downloadFile = async (url, filename) => {
    try {
      const response = await axios.get(url, { responseType: 'blob' });
      const blob = new Blob([response.data]);
      const link = document.createElement('a');
      link.href = window.URL.createObjectURL(blob);
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(link.href);
    } catch (error) {
      console.error('Download failed:', error);
      alert('Failed to download file');
    }
  };

  useEffect(() => {
    if (activeTab === 'api-keys' && apiKeys.length === 0) {
      loadApiKeys();
    }
    if (activeTab === 'activity' && recentActivity.length === 0) {
      loadRecentActivity();
    }
    if (activeTab === 'user-stats' && userStats.length === 0) {
      loadUserStats();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  if (loading && !stats) {
    return <div className="loading">Loading dashboard...</div>;
  }

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="admin-dashboard">
      <header className="dashboard-header">
        <div>
          <h1>🔧 Admin Dashboard</h1>
        </div>
        <div className="header-actions">
          <span className="user-info">👤 {user?.name || user?.email}</span>
          <button onClick={loadDashboardData} className="refresh-btn">🔄 Refresh</button>
          <button onClick={handleLogout} className="btn-logout">Logout</button>
        </div>
      </header>

      <div className="dashboard-layout">
        <aside className="sidebar">
          <nav className="sidebar-nav">
            <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>
              <span className="icon">📊</span> Overview
            </button>
            <button className={activeTab === 'users' ? 'active' : ''} onClick={() => setActiveTab('users')}>
              <span className="icon">👥</span> Users
            </button>
            <button className={activeTab === 'submissions' ? 'active' : ''} onClick={() => setActiveTab('submissions')}>
              <span className="icon">📄</span> Submissions
            </button>
            <button className={activeTab === 'audit' ? 'active' : ''} onClick={() => setActiveTab('audit')}>
              <span className="icon">📋</span> Audit Logs
            </button>
            <button className={activeTab === 'analytics' ? 'active' : ''} onClick={() => setActiveTab('analytics')}>
              <span className="icon">📈</span> Analytics
            </button>
            <button className={activeTab === 'api-keys' ? 'active' : ''} onClick={() => { setActiveTab('api-keys'); loadApiKeys(); }}>
              <span className="icon">🔑</span> API Keys
            </button>
            <button className={activeTab === 'activity' ? 'active' : ''} onClick={() => { setActiveTab('activity'); loadRecentActivity(); }}>
              <span className="icon">🔔</span> Activity
            </button>
            <button className={activeTab === 'user-stats' ? 'active' : ''} onClick={() => { setActiveTab('user-stats'); loadUserStats(); }}>
              <span className="icon">📊</span> User Stats
            </button>
          </nav>
        </aside>

        <main className="dashboard-content">

      {activeTab === 'upload' && (
        <div className="upload-section">
          <UploadForm onUploadSuccess={(id) => { alert(`Manuscript uploaded successfully! Submission ID: ${id}`); loadDashboardData(); }} />
        </div>
      )}

      {activeTab === 'overview' && stats && (
        <div className="overview-section">
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Users</h3>
              <p className="stat-value">{stats.total_users}</p>
            </div>
            <div className="stat-card">
              <h3>Active Users</h3>
              <p className="stat-value">{stats.active_users}</p>
            </div>
            <div className="stat-card">
              <h3>Total Submissions</h3>
              <p className="stat-value">{stats.total_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Pending</h3>
              <p className="stat-value">{stats.pending_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Processing</h3>
              <p className="stat-value">{stats.processing_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Completed</h3>
              <p className="stat-value">{stats.completed_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Failed</h3>
              <p className="stat-value">{stats.failed_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Recent Activity (24h)</h3>
              <p className="stat-value">{stats.recent_activity_count}</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'users' && (
        <div className="users-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>User Management</h2>
            <button onClick={() => setShowResetPassword(!showResetPassword)} className="create-key-btn">
              {showResetPassword ? '❌ Cancel' : '🔑 Reset Password'}
            </button>
          </div>
          <p className="info-note">ℹ️ Note: Admins cannot view or modify Super Admin accounts</p>

          {showResetPassword && (
            <div className="create-key-form">
              <h3>Reset User Password</h3>
              <form onSubmit={resetPassword}>
                <div className="form-group">
                  <label>Email or Username *</label>
                  <input
                    type="text"
                    value={resetPasswordData.identifier}
                    onChange={(e) => setResetPasswordData({...resetPasswordData, identifier: e.target.value})}
                    required
                    placeholder="email@example.com or username"
                  />
                </div>
                <div className="form-group">
                  <label>New Password *</label>
                  <div style={{ position: 'relative' }}>
                    <input
                      type={showResetPasswordField ? "text" : "password"}
                      value={resetPasswordData.new_password}
                      onChange={(e) => setResetPasswordData({...resetPasswordData, new_password: e.target.value})}
                      required
                      minLength="8"
                      placeholder="Min 8 characters"
                      style={{ paddingRight: '40px' }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowResetPasswordField(!showResetPasswordField)}
                      className="password-toggle"
                      title={showResetPasswordField ? "Hide password" : "Show password"}
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
                    >
                      {showResetPasswordField ? '👁️' : '👁️🗨️'}
                    </button>
                  </div>
                </div>
                <button type="submit" className="submit-btn">Reset Password</button>
              </form>
            </div>
          )}
          <table className="data-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user._id}>
                  <td>{user.email}</td>
                  <td>{user.name}</td>
                  <td><span className="role-badge">{user.role}</span></td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  <td>
                    <button onClick={() => toggleUserStatus(user._id, user.is_active)} className="action-btn">
                      {user.is_active ? '🚫 Deactivate' : '✅ Activate'}
                    </button>
                    <button
                      onClick={() => {
                        setResetPasswordData({ identifier: user.email, new_password: '' });
                        setShowResetPassword(true);
                      }}
                      className="action-btn"
                      title="Reset password"
                    >
                      🔑 Reset
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'submissions' && (
        <div className="submissions-section">
          <h2>Submissions Management</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Domain</th>
                <th>Status</th>
                <th>Created</th>
                <th>Completed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {submissions.map(sub => (
                <tr key={sub._id}>
                  <td>{sub.title}</td>
                  <td>{sub.detected_domain || 'N/A'}</td>
                  <td>
                    <span className={`status-badge ${sub.status}`}>
                      {sub.status}
                    </span>
                  </td>
                  <td>{new Date(sub.created_at).toLocaleDateString()}</td>
                  <td>{sub.completed_at ? new Date(sub.completed_at).toLocaleDateString() : 'N/A'}</td>
                  <td>
                    <button
                      onClick={() => downloadFile(`/api/v1/downloads/manuscripts/${sub._id}`, sub.title)}
                      className="action-btn"
                      title="Download original manuscript"
                    >
                      📄 Manuscript
                    </button>
                    {sub.status === 'completed' && (
                      <button
                        onClick={() => {
                          const baseName = sub.title.replace(/\.[^/.]+$/, '');
                          downloadFile(`/api/v1/downloads/reviews/${sub._id}`, `${baseName}_Reviewed.pdf`);
                        }}
                        className="action-btn"
                        title="Download review PDF"
                      >
                        📋 Review
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="audit-section">
          <h2>Audit Logs (Last 7 Days)</h2>
          <p className="info-note">ℹ️ Note: Admins can view logs up to 30 days</p>
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>User ID</th>
                <th>IP Address</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {auditLogs.map(log => (
                <tr key={log._id}>
                  <td>{new Date(log.timestamp).toLocaleString()}</td>
                  <td>{log.event_type}</td>
                  <td>{log.user_id || 'N/A'}</td>
                  <td>{log.ip_address || 'N/A'}</td>
                  <td>
                    <span className={`severity-badge ${log.severity}`}>
                      {log.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'analytics' && analytics && (
        <div className="analytics-section">
          <h2>Submission Analytics (Last 30 Days)</h2>
          <div className="analytics-chart">
            {analytics.analytics.map(day => (
              <div key={day._id} className="chart-bar">
                <div className="bar-label">{day._id}</div>
                <div className="bar-container">
                  <div className="bar completed" style={{width: `${(day.completed / day.count) * 100}%`}}>
                    {day.completed}
                  </div>
                  <div className="bar failed" style={{width: `${(day.failed / day.count) * 100}%`}}>
                    {day.failed}
                  </div>
                </div>
                <div className="bar-total">Total: {day.count}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'api-keys' && (
        <div className="api-keys-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>API Key Management</h2>
            <button onClick={() => setShowCreateKey(!showCreateKey)} className="create-key-btn">
              {showCreateKey ? '❌ Cancel' : '➕ Create API Key'}
            </button>
          </div>
          <p className="info-note">ℹ️ Note: Admins cannot create or view Super Admin API keys</p>

          {showCreateKey && (
            <div className="create-key-form">
              <h3>Create New API Key</h3>
              <form onSubmit={createApiKey}>
                <div className="form-group">
                  <label>Name *</label>
                  <input
                    type="text"
                    value={newKey.name}
                    onChange={(e) => setNewKey({...newKey, name: e.target.value})}
                    required
                    placeholder="e.g., Production API Key"
                  />
                </div>
                <div className="form-group">
                  <label>Role *</label>
                  <select
                    value={newKey.role}
                    onChange={(e) => setNewKey({...newKey, role: e.target.value})}
                    required
                  >
                    <option value="author">Author</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Expires In (days) *</label>
                  <input
                    type="number"
                    value={newKey.expires_days}
                    onChange={(e) => setNewKey({...newKey, expires_days: parseInt(e.target.value)})}
                    required
                    min="1"
                    max="365"
                  />
                </div>
                <button type="submit" className="submit-btn">Create API Key</button>
              </form>
            </div>
          )}

          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Key</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Expires</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map(key => (
                <tr key={key._id}>
                  <td>{key.name}</td>
                  <td><code>{key.key}</code></td>
                  <td>{key.role}</td>
                  <td>
                    <span className={`status-badge ${key.is_active ? 'active' : 'inactive'}`}>
                      {key.is_active ? 'Active' : 'Revoked'}
                    </span>
                  </td>
                  <td>{new Date(key.created_at).toLocaleDateString()}</td>
                  <td>{key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="activity-section">
          <h2>Recent System Activity</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>User ID</th>
                <th>Severity</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {recentActivity.map(activity => (
                <tr key={activity._id}>
                  <td>{new Date(activity.timestamp).toLocaleString()}</td>
                  <td>{activity.event_type}</td>
                  <td>{activity.user_id || 'System'}</td>
                  <td>
                    <span className={`severity-badge ${activity.severity}`}>
                      {activity.severity}
                    </span>
                  </td>
                  <td>{JSON.stringify(activity.details || {})}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'user-stats' && (
        <div className="user-stats-section">
          <h2>User Statistics by Role</h2>
          <div className="stats-grid">
            {userStats.map(stat => (
              <div key={stat._id} className="stat-card">
                <h3>{stat._id || 'Unknown'}</h3>
                <p className="stat-value">{stat.count}</p>
              </div>
            ))}
          </div>
        </div>
      )}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
