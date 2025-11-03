import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import authService from '../services/authService';
import './EditorDashboard.css';

const EditorDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [stats, setStats] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [domains, setDomains] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [statusFilter, setStatusFilter] = useState('');
  const [showDecisionModal, setShowDecisionModal] = useState(false);
  const [decision, setDecision] = useState({ decision: '', comments: '' });

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, submissionsRes, analyticsRes, domainsRes, perfRes] = await Promise.all([
        axios.get('/api/v1/editor/dashboard/stats'),
        axios.get('/api/v1/editor/submissions?limit=50'),
        axios.get('/api/v1/editor/analytics/submissions?days=30'),
        axios.get('/api/v1/editor/analytics/domains'),
        axios.get('/api/v1/editor/analytics/performance'),
      ]);

      setStats(statsRes.data);
      setSubmissions(submissionsRes.data.submissions);
      setAnalytics(analyticsRes.data.analytics);
      setDomains(domainsRes.data.domains);
      setPerformance(perfRes.data.performance);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSubmissionDetails = async (submissionId) => {
    try {
      const res = await axios.get(`/api/v1/editor/submissions/${submissionId}`);
      setSelectedSubmission(res.data);
    } catch (error) {
      console.error('Failed to fetch submission details:', error);
    }
  };

  const handleMakeDecision = async () => {
    if (!decision.decision || !decision.comments) {
      alert('Please provide decision and comments');
      return;
    }

    try {
      await axios.post(`/api/v1/editor/submissions/${selectedSubmission._id}/decision`, decision);
      alert('Editorial decision recorded successfully');
      setShowDecisionModal(false);
      setDecision({ decision: '', comments: '' });
      fetchDashboardData();
    } catch (error) {
      console.error('Failed to record decision:', error);
      alert('Failed to record decision');
    }
  };

  const handleReprocess = async (submissionId) => {
    if (!window.confirm('Reprocess this submission?')) return;

    try {
      await axios.post(`/api/v1/editor/submissions/${submissionId}/reprocess`);
      alert('Submission queued for reprocessing');
      fetchDashboardData();
    } catch (error) {
      console.error('Failed to reprocess:', error);
      alert('Failed to reprocess submission');
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (ms) => {
    if (!ms) return 'N/A';
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  if (loading) {
    return <div className="editor-dashboard loading">Loading dashboard...</div>;
  }

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="editor-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Editor Dashboard</h1>
          <p>Manage manuscript submissions and make editorial decisions</p>
        </div>
        <div className="user-info">
          <span>👤 {user?.name || user?.email}</span>
          <button onClick={handleLogout} className="btn-logout">Logout</button>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={activeTab === 'submissions' ? 'active' : ''} onClick={() => setActiveTab('submissions')}>All Submissions</button>
        <button className={activeTab === 'analytics' ? 'active' : ''} onClick={() => setActiveTab('analytics')}>Analytics</button>
      </div>

      {activeTab === 'overview' && (
        <div className="overview-tab">
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Submissions</h3>
              <p className="stat-value">{stats?.total_submissions || 0}</p>
            </div>
            <div className="stat-card warning">
              <h3>Pending Review</h3>
              <p className="stat-value">{stats?.pending_review || 0}</p>
            </div>
            <div className="stat-card info">
              <h3>In Review</h3>
              <p className="stat-value">{stats?.in_review || 0}</p>
            </div>
            <div className="stat-card success">
              <h3>Completed</h3>
              <p className="stat-value">{stats?.completed || 0}</p>
            </div>
            <div className="stat-card danger">
              <h3>Failed</h3>
              <p className="stat-value">{stats?.failed || 0}</p>
            </div>
            <div className="stat-card">
              <h3>Today</h3>
              <p className="stat-value">{stats?.today_submissions || 0}</p>
            </div>
            <div className="stat-card">
              <h3>This Week</h3>
              <p className="stat-value">{stats?.this_week || 0}</p>
            </div>
          </div>

          {performance && (
            <div className="performance-card">
              <h3>Review Performance</h3>
              <div className="performance-stats">
                <div>
                  <span>Average Time:</span>
                  <strong>{formatDuration(performance.avg_time_ms)}</strong>
                </div>
                <div>
                  <span>Fastest:</span>
                  <strong>{formatDuration(performance.min_time_ms)}</strong>
                </div>
                <div>
                  <span>Slowest:</span>
                  <strong>{formatDuration(performance.max_time_ms)}</strong>
                </div>
                <div>
                  <span>Total Reviews:</span>
                  <strong>{performance.total_reviews || 0}</strong>
                </div>
              </div>
            </div>
          )}

          <div className="recent-submissions">
            <h3>Recent Submissions</h3>
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Author</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Submitted</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {submissions.slice(0, 10).map(sub => (
                  <tr key={sub._id}>
                    <td>{sub.title}</td>
                    <td>{sub.user_id || 'Unknown'}</td>
                    <td>{sub.detected_domain || 'Unknown'}</td>
                    <td><span className={`status-badge ${sub.status}`}>{sub.status}</span></td>
                    <td>{formatDate(sub.created_at)}</td>
                    <td>
                      <button onClick={() => { fetchSubmissionDetails(sub._id); setActiveTab('submissions'); }} className="btn-view">View</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'submissions' && (
        <div className="submissions-tab">
          <div className="submissions-header">
            <h3>All Submissions</h3>
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Status</option>
              <option value="pending">Pending</option>
              <option value="processing">Processing</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="submissions-list">
            {submissions
              .filter(s => !statusFilter || s.status === statusFilter)
              .map(sub => (
                <div key={sub._id} className="submission-card">
                  <div className="submission-header">
                    <h4>{sub.title}</h4>
                    <span className={`status-badge ${sub.status}`}>{sub.status}</span>
                  </div>
                  <div className="submission-details">
                    <p><strong>Author:</strong> {sub.user_id || 'Unknown'}</p>
                    <p><strong>Domain:</strong> {sub.detected_domain || 'Unknown'}</p>
                    <p><strong>Submitted:</strong> {formatDate(sub.created_at)}</p>
                    {sub.completed_at && <p><strong>Completed:</strong> {formatDate(sub.completed_at)}</p>}
                    {sub.editorial_decision && (
                      <p><strong>Decision:</strong> {sub.editorial_decision.decision}</p>
                    )}
                  </div>
                  <div className="submission-actions">
                    <button onClick={() => fetchSubmissionDetails(sub._id)} className="btn-view">View Details</button>
                    <button 
                      onClick={() => downloadFile(`/api/v1/downloads/manuscripts/${sub._id}`, sub.title)} 
                      className="btn-download"
                      title="Download original manuscript"
                    >
                      📄 Manuscript
                    </button>
                    {sub.status === 'completed' && (
                      <>
                        <button 
                          onClick={() => {
                            const baseName = sub.title.replace(/\.[^/.]+$/, '');
                            const ext = sub.title.match(/\.[^/.]+$/)?.[0] || '.pdf';
                            downloadFile(`/api/v1/downloads/reviews/${sub._id}`, `${baseName}_Reviewed${ext}`);
                          }} 
                          className="btn-download"
                          title="Download review PDF"
                        >
                          📋 Review
                        </button>
                        <button onClick={() => { setSelectedSubmission(sub); setShowDecisionModal(true); }} className="btn-decision">Make Decision</button>
                      </>
                    )}
                    {sub.status === 'failed' && (
                      <button onClick={() => handleReprocess(sub._id)} className="btn-reprocess">Reprocess</button>
                    )}
                  </div>
                </div>
              ))}
          </div>

          {selectedSubmission && !showDecisionModal && (
            <div className="submission-detail-modal">
              <div className="modal-content">
                <div className="modal-header">
                  <h3>Submission Details</h3>
                  <button onClick={() => setSelectedSubmission(null)} className="btn-close">×</button>
                </div>
                <div className="modal-body">
                  <h4>{selectedSubmission.title}</h4>
                  <p><strong>Status:</strong> {selectedSubmission.status}</p>
                  <p><strong>Domain:</strong> {selectedSubmission.detected_domain}</p>
                  <p><strong>Submitted:</strong> {formatDate(selectedSubmission.created_at)}</p>
                  {selectedSubmission.agent_tasks && (
                    <div className="agent-tasks">
                      <h5>Agent Tasks</h5>
                      {selectedSubmission.agent_tasks.map(task => (
                        <div key={task._id} className="task-item">
                          <strong>{task.agent_type}:</strong> {task.status}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="analytics-tab">
          <div className="analytics-section">
            <h3>Submission Timeline (Last 30 Days)</h3>
            <div className="timeline-chart">
              {analytics && analytics.length > 0 ? (
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Total</th>
                      <th>Completed</th>
                      <th>Failed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.map(item => (
                      <tr key={item._id}>
                        <td>{item._id}</td>
                        <td>{item.count}</td>
                        <td>{item.completed}</td>
                        <td>{item.failed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No data available</p>
              )}
            </div>
          </div>

          <div className="analytics-section">
            <h3>Domain Distribution</h3>
            <div className="domain-chart">
              {domains.length > 0 ? (
                <table>
                  <thead>
                    <tr>
                      <th>Domain</th>
                      <th>Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {domains.map(item => (
                      <tr key={item._id}>
                        <td>{item._id || 'Unknown'}</td>
                        <td>{item.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No domain data available</p>
              )}
            </div>
          </div>
        </div>
      )}

      {showDecisionModal && (
        <div className="decision-modal">
          <div className="modal-content">
            <div className="modal-header">
              <h3>Make Editorial Decision</h3>
              <button onClick={() => setShowDecisionModal(false)} className="btn-close">×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Decision:</label>
                <select value={decision.decision} onChange={(e) => setDecision({ ...decision, decision: e.target.value })}>
                  <option value="">Select Decision</option>
                  <option value="accept">Accept</option>
                  <option value="revise">Revise & Resubmit</option>
                  <option value="reject">Reject</option>
                </select>
              </div>
              <div className="form-group">
                <label>Comments:</label>
                <textarea
                  value={decision.comments}
                  onChange={(e) => setDecision({ ...decision, comments: e.target.value })}
                  rows="6"
                  placeholder="Enter your editorial comments..."
                />
              </div>
              <div className="modal-actions">
                <button onClick={handleMakeDecision} className="btn-submit">Submit Decision</button>
                <button onClick={() => setShowDecisionModal(false)} className="btn-cancel">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default EditorDashboard;
