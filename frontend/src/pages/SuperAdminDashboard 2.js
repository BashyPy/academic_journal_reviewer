import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import authService from '../services/authService';
import './SuperAdminDashboard.css';

const SuperAdminDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [apiKeys, setApiKeys] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [userActivity, setUserActivity] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');

  const [loading, setLoading] = useState(false);
  const [showCreateUser, setShowCreateUser] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    password: '',
    name: '',
    role: 'author',
    username: ''
  });
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [resetPasswordData, setResetPasswordData] = useState({
    user_id: '',
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
        axios.get('/api/v1/super-admin/dashboard/stats'),
        axios.get('/api/v1/super-admin/users?limit=10'),
        axios.get('/api/v1/super-admin/submissions?limit=10'),
        axios.get('/api/v1/super-admin/audit-logs?limit=20'),
        axios.get('/api/v1/super-admin/analytics/submissions?days=30'),
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
      const res = await axios.get('/api/v1/super-admin/api-keys');
      setApiKeys(res.data.api_keys);
    } catch (error) {
      console.error('Failed to load API keys:', error);
    }
  };

  const loadPerformance = async () => {
    try {
      const res = await axios.get('/api/v1/super-admin/analytics/performance');
      setPerformance(res.data.performance);
    } catch (error) {
      console.error('Failed to load performance metrics:', error);
    }
  };

  const loadUserActivity = async () => {
    try {
      const res = await axios.get('/api/v1/super-admin/analytics/user-activity?days=7');
      setUserActivity(res.data.user_activity);
    } catch (error) {
      console.error('Failed to load user activity:', error);
    }
  };

  const updateUserRole = async (userId, newRole) => {
    try {
      await axios.patch(`/api/v1/super-admin/users/${userId}/role?role=${newRole}`);
      alert('User role updated successfully');
      loadDashboardData();
    } catch (error) {
      alert('Failed to update user role');
    }
  };

  const toggleUserStatus = async (userId, isActive) => {
    try {
      await axios.patch(`/api/v1/super-admin/users/${userId}/status?is_active=${!isActive}`);
      alert(`User ${!isActive ? 'activated' : 'deactivated'} successfully`);
      loadDashboardData();
    } catch (error) {
      alert('Failed to update user status');
    }
  };

  const deleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;

    try {
      await axios.delete(`/api/v1/super-admin/users/${userId}`);
      alert('User deleted successfully');
      loadDashboardData();
    } catch (error) {
      alert('Failed to delete user');
    }
  };

  const clearCache = async () => {
    try {
      await axios.post('/api/v1/super-admin/system/clear-cache');
      alert('System cache cleared successfully');
    } catch (error) {
      alert('Failed to clear cache');
    }
  };

  const revokeApiKey = async (keyId) => {
    if (!window.confirm('Are you sure you want to revoke this API key?')) return;
    try {
      await axios.delete(`/api/v1/super-admin/api-keys/${keyId}`);
      alert('API key revoked successfully');
      loadApiKeys();
    } catch (error) {
      alert('Failed to revoke API key');
    }
  };

  const reprocessSubmission = async (submissionId) => {
    if (!window.confirm('Reprocess this submission?')) return;
    try {
      await axios.post(`/api/v1/super-admin/submissions/${submissionId}/reprocess`);
      alert('Submission queued for reprocessing');
      loadDashboardData();
    } catch (error) {
      alert('Failed to reprocess submission');
    }
  };

  const deleteSubmission = async (submissionId) => {
    if (!window.confirm('Are you sure you want to delete this submission?')) return;
    try {
      await axios.delete(`/api/v1/super-admin/submissions/${submissionId}`);
      alert('Submission deleted successfully');
      loadDashboardData();
    } catch (error) {
      alert('Failed to delete submission');
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

  const createUser = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/v1/super-admin/users/create', newUser);
      alert('User created successfully');
      setShowCreateUser(false);
      setNewUser({ email: '', password: '', name: '', role: 'author', username: '' });
      loadDashboardData();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create user');
    }
  };

  const resetPassword = async (e) => {
    e.preventDefault();
    if (!window.confirm('Reset password for this user?')) return;

    try {
      await axios.post('/api/v1/super-admin/users/reset-password', resetPasswordData);
      alert('Password reset successfully');
      setShowResetPassword(false);
      setResetPasswordData({ user_id: '', new_password: '' });
      setShowResetPasswordField(false);
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to reset password');
    }
  };

  useEffect(() => {
    if (activeTab === 'api-keys' && apiKeys.length === 0) {
      loadApiKeys();
    }
    if (activeTab === 'performance' && !performance) {
      loadPerformance();
    }
    if (activeTab === 'activity' && userActivity.length === 0) {
      loadUserActivity();
    }
  }, [activeTab, apiKeys.length, performance, userActivity.length]);

  if (loading && !stats) {
    return <div className="loading">Loading dashboard...</div>;
  }

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="super-admin-dashboard">
      <header className="dashboard-header">
        <div>
          <h1>🛡️ Super Admin Dashboard</h1>
        </div>
        <div className="header-actions">
          <span className="user-info">👤 {user?.name || user?.email}</span>
          <button onClick={() => navigate('/')} className="refresh-btn">🏠 Home</button>
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
            <button className={activeTab === 'upload' ? 'active' : ''} onClick={() => setActiveTab('upload')}>
              <span className="icon">📤</span> Upload Manuscript
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
            <button className={activeTab === 'performance' ? 'active' : ''} onClick={() => { setActiveTab('performance'); loadPerformance(); }}>
              <span className="icon">⚡</span> Performance
            </button>
            <button className={activeTab === 'activity' ? 'active' : ''} onClick={() => { setActiveTab('activity'); loadUserActivity(); }}>
              <span className="icon">🔔</span> Activity
            </button>
            <button className={activeTab === 'system' ? 'active' : ''} onClick={() => setActiveTab('system')}>
              <span className="icon">⚙️</span> System
            </button>
          </nav>
        </aside>

        <main className="dashboard-content">

      {activeTab === 'upload' && (
        <div className="upload-section">
          <h2>Upload Manuscript</h2>
          <iframe
            src="/"
            style={{ width: '100%', height: '600px', border: 'none', borderRadius: '8px' }}
            title="Upload Manuscript"
          />
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
              <h3>Total Submissions</h3>
              <p className="stat-value">{stats.total_submissions}</p>
            </div>
            <div className="stat-card">
              <h3>Active Reviews</h3>
              <p className="stat-value">{stats.active_reviews}</p>
            </div>
            <div className="stat-card">
              <h3>Completed Reviews</h3>
              <p className="stat-value">{stats.completed_reviews}</p>
            </div>
            <div className="stat-card">
              <h3>Failed Reviews</h3>
              <p className="stat-value">{stats.failed_reviews}</p>
            </div>
            <div className="stat-card">
              <h3>Audit Logs</h3>
              <p className="stat-value">{stats.total_audit_logs}</p>
            </div>
          </div>

          {stats.security_stats && (
            <div className="security-stats">
              <h2>Security Statistics</h2>
              <div className="stats-grid">
                <div className="stat-card">
                  <h3>Blocked IPs</h3>
                  <p className="stat-value">{stats.security_stats.blocked_ips || 0}</p>
                </div>
                <div className="stat-card">
                  <h3>Failed Logins</h3>
                  <p className="stat-value">{stats.security_stats.failed_logins || 0}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'users' && (
        <div className="users-section">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h2>User Management</h2>
            <div>
              <button onClick={() => setShowResetPassword(!showResetPassword)} className="create-user-btn" style={{ marginRight: '10px' }}>
                {showResetPassword ? '❌ Cancel Reset' : '🔑 Reset Password'}
              </button>
              <button onClick={() => setShowCreateUser(!showCreateUser)} className="create-user-btn">
                {showCreateUser ? '❌ Cancel' : '➕ Create User'}
              </button>
            </div>
          </div>

          {showResetPassword && (
            <div className="create-user-form">
              <h3>Reset User Password</h3>
              <form onSubmit={resetPassword}>
                <div className="form-group">
                  <label>Select User *</label>
                  <select
                    value={resetPasswordData.user_id}
                    onChange={(e) => setResetPasswordData({...resetPasswordData, user_id: e.target.value})}
                    required
                  >
                    <option value="">-- Select User --</option>
                    {users.map(user => (
                      <option key={user._id} value={user._id}>
                        {user.name} ({user.email}) - {user.role}
                      </option>
                    ))}
                  </select>
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
                    >
                      {showResetPasswordField ? '👁️' : '👁️🗨️'}
                    </button>
                  </div>
                </div>
                <button type="submit" className="submit-btn">Reset Password</button>
              </form>
            </div>
          )}

          {showCreateUser && (
            <div className="create-user-form">
              <h3>Create New User Account</h3>
              <form onSubmit={createUser}>
                <div className="form-row">
                  <div className="form-group">
                    <label>Email *</label>
                    <input
                      type="email"
                      value={newUser.email}
                      onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                      required
                      placeholder="user@example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label>Name *</label>
                    <input
                      type="text"
                      value={newUser.name}
                      onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                      required
                      placeholder="Full Name"
                    />
                  </div>
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label>Username (optional)</label>
                    <input
                      type="text"
                      value={newUser.username}
                      onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                      placeholder="username"
                    />
                  </div>
                  <div className="form-group">
                    <label>Password *</label>
                    <div style={{ position: 'relative' }}>
                      <input
                        type={showPassword ? "text" : "password"}
                        value={newUser.password}
                        onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                        required
                        minLength="8"
                        placeholder="Min 8 characters"
                        style={{ paddingRight: '40px' }}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="password-toggle"
                        title={showPassword ? "Hide password" : "Show password"}
                      >
                        {showPassword ? '👁️' : '👁️‍🗨️'}
                      </button>
                    </div>
                  </div>
                </div>
                <div className="form-group">
                  <label>Role *</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                    required
                  >
                    <option value="author">Author</option>
                    <option value="reviewer">Reviewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                    <option value="super_admin">Super Admin</option>
                  </select>
                </div>
                <button type="submit" className="submit-btn">Create User Account</button>
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
                  <td>
                    <select
                      value={user.role}
                      onChange={(e) => updateUserRole(user._id, e.target.value)}
                      className="role-select"
                    >
                      <option value="author">Author</option>
                      <option value="reviewer">Reviewer</option>
                      <option value="editor">Editor</option>
                      <option value="admin">Admin</option>
                      <option value="super_admin">Super Admin</option>
                    </select>
                  </td>
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
                        setResetPasswordData({ user_id: user._id, new_password: '' });
                        setShowResetPassword(true);
                      }}
                      className="action-btn"
                      title="Reset password"
                    >
                      🔑 Reset
                    </button>
                    <button onClick={() => deleteUser(user._id)} className="action-btn danger">🗑️ Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'submissions' && (
        <div className="submissions-section">
          <h2>Recent Submissions</h2>
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
                          const ext = sub.title.match(/\.[^/.]+$/)?.[0] || '.pdf';
                          downloadFile(`/api/v1/downloads/reviews/${sub._id}`, `${baseName}_Reviewed${ext}`);
                        }}
                        className="action-btn"
                        title="Download review PDF"
                      >
                        📋 Review
                      </button>
                    )}
                    {sub.status === 'failed' && (
                      <button onClick={() => reprocessSubmission(sub._id)} className="action-btn">🔄 Reprocess</button>
                    )}
                    <button onClick={() => deleteSubmission(sub._id)} className="action-btn danger">🗑️ Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="audit-section">
          <h2>Audit Logs</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Event Type</th>
                <th>User ID</th>
                <th>IP Address</th>
                <th>Severity</th>
                <th>Details</th>
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
                  <td>{JSON.stringify(log.details)}</td>
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
          <h2>API Key Management</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Key</th>
                <th>Role</th>
                <th>Status</th>
                <th>Created</th>
                <th>Expires</th>
                <th>Actions</th>
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
                  <td>
                    {key.is_active && (
                      <button onClick={() => revokeApiKey(key._id)} className="action-btn danger">🚫 Revoke</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'performance' && performance && (
        <div className="performance-section">
          <h2>System Performance Metrics</h2>
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Average Processing Time</h3>
              <p className="stat-value">{(performance.avg_time_ms / 1000 / 60).toFixed(2)} min</p>
            </div>
            <div className="stat-card">
              <h3>Fastest Processing</h3>
              <p className="stat-value">{(performance.min_time_ms / 1000 / 60).toFixed(2)} min</p>
            </div>
            <div className="stat-card">
              <h3>Slowest Processing</h3>
              <p className="stat-value">{(performance.max_time_ms / 1000 / 60).toFixed(2)} min</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'activity' && (
        <div className="activity-section">
          <h2>User Activity (Last 7 Days)</h2>
          <table className="data-table">
            <thead>
              <tr>
                <th>User ID</th>
                <th>Event Count</th>
                <th>Last Activity</th>
              </tr>
            </thead>
            <tbody>
              {userActivity.map((activity, idx) => (
                <tr key={idx}>
                  <td>{activity._id || 'Anonymous'}</td>
                  <td>{activity.event_count}</td>
                  <td>{new Date(activity.last_activity).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'system' && (
        <div className="system-section">
          <h2>System Management</h2>
          <div className="system-actions">
            <button onClick={clearCache} className="system-btn">🗑️ Clear System Cache</button>
            <button onClick={loadDashboardData} className="system-btn">🔄 Refresh All Data</button>
          </div>
        </div>
      )}
        </main>
      </div>
    </div>
  );
};

export default SuperAdminDashboard;
