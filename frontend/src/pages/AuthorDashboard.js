import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import authService from '../services/authService';
import rateLimiter from '../services/rateLimiter';
import './AuthorDashboard.css';

const AuthorDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [stats, setStats] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [domains, setDomains] = useState([]);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [statusFilter, setStatusFilter] = useState('');
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [uploadProcessing, setUploadProcessing] = useState(false);
  const [uploadCompleted, setUploadCompleted] = useState(false);
  const [uploadSubmissionId, setUploadSubmissionId] = useState(null);
  const [uploadSubmissionData, setUploadSubmissionData] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    let interval;
    if (uploadProcessing && uploadSubmissionId) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`/api/v1/submissions/${uploadSubmissionId}/report`);
          if (!response.data.processing) {
            setUploadProcessing(false);
            setUploadCompleted(true);
            setUploadSubmissionData(response.data);
            clearInterval(interval);
            fetchDashboardData();
          }
        } catch (err) {
          console.error('Status check error:', err);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [uploadProcessing, uploadSubmissionId]);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, submissionsRes, timelineRes, domainsRes, perfRes] = await Promise.all([
        axios.get('/api/v1/author/dashboard/stats'),
        axios.get('/api/v1/author/submissions?limit=10'),
        axios.get('/api/v1/author/analytics/timeline?days=30'),
        axios.get('/api/v1/author/analytics/domains'),
        axios.get('/api/v1/author/analytics/performance'),
      ]);

      setStats(statsRes.data);
      setSubmissions(submissionsRes.data.submissions);
      setTimeline(timelineRes.data.timeline);
      setDomains(domainsRes.data.domains);
      setPerformance(perfRes.data.performance);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSubmission = async (submissionId) => {
    if (!window.confirm('Are you sure you want to delete this submission?')) return;

    try {
      await axios.delete(`/api/v1/author/submissions/${submissionId}`);
      setSubmissions(submissions.filter(s => s._id !== submissionId));
      fetchDashboardData();
    } catch (error) {
      console.error('Failed to delete submission:', error);
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (ms) => {
    if (!ms || ms === 0 || isNaN(ms)) return '0m 0s';
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    return `${minutes}m ${seconds}s`;
  };

  const handleFileChange = (selectedFile) => {
    if (selectedFile) {
      const fileExt = selectedFile.name.split('.').pop().toLowerCase();
      if (!['pdf', 'docx'].includes(fileExt)) {
        setUploadError('Only PDF and DOCX files are allowed');
        setFile(null);
        return;
      }
      setUploadError('');
      setFile(selectedFile);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileChange(e.dataTransfer.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      setUploadError('Please select a file');
      return;
    }

    setUploading(true);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await rateLimiter.makeRequest('upload', () =>
        axios.post('/api/v1/submissions/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      );
      const subId = response.data.submission_id;
      setUploadSubmissionId(subId);
      setUploadProcessing(true);
      setFile(null);
    } catch (err) {
      setUploadError(err.response?.data?.detail || err.message || 'Network error occurred');
    } finally {
      setUploading(false);
    }
  };

  const handleViewReview = () => {
    window.open(`/review/${uploadSubmissionId}`, '_blank');
  };

  const handleDownloadReview = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${uploadSubmissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const baseName = uploadSubmissionData?.title?.replace(/\.[^/.]+$/, '') || 'review';
      link.setAttribute('download', `${baseName}_reviewed.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      setUploadError('Failed to download review');
    }
  };

  const handleNewUpload = () => {
    setUploadCompleted(false);
    setUploadProcessing(false);
    setUploadSubmissionId(null);
    setUploadSubmissionData(null);
    setFile(null);
    setUploadError('');
  };

  if (loading) {
    return <div className="author-dashboard loading">Loading dashboard...</div>;
  }

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="author-dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Author Dashboard</h1>
          <p>Track your manuscript submissions and reviews</p>
        </div>
        <div className="user-info">
          <span>👤 {user?.name || user?.email}</span>
          <button onClick={handleLogout} className="btn-logout">Logout</button>
        </div>
      </div>

      <div className="dashboard-tabs">
        <button className={activeTab === 'overview' ? 'active' : ''} onClick={() => setActiveTab('overview')}>Overview</button>
        <button className={activeTab === 'upload' ? 'active' : ''} onClick={() => setActiveTab('upload')}>📤 Upload Manuscript</button>
        <button className={activeTab === 'submissions' ? 'active' : ''} onClick={() => setActiveTab('submissions')}>My Submissions</button>
        <button className={activeTab === 'analytics' ? 'active' : ''} onClick={() => setActiveTab('analytics')}>Analytics</button>
      </div>

      {activeTab === 'upload' && (
        <div className="upload-tab">
          <div className="upload-card">
            <div className="upload-header">
              <h3>📄 Upload Academic Manuscript</h3>
              <p>Submit your PDF or DOCX file for comprehensive AI-powered review</p>
            </div>

            <div
              className={`file-drop-zone ${dragOver ? 'dragover' : ''}`}
              onDrop={handleDrop}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={(e) => { e.preventDefault(); setDragOver(false); }}
              onClick={() => document.getElementById('file-input').click()}
            >
              <div className="drop-content">
                <div className="drop-icon">📁</div>
                <p className="drop-title">Drop your file here or click to browse</p>
                <p className="drop-subtitle">Supported formats: PDF, DOCX • Maximum size: 50MB</p>
              </div>
            </div>

            <input
              id="file-input"
              type="file"
              onChange={(e) => handleFileChange(e.target.files[0])}
              accept=".pdf,.docx"
              style={{ display: 'none' }}
            />

            {file && (
              <div className="selected-file">
                <span>📎 {file.name}</span>
                <span className="file-size">({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            )}

            {uploadError && <div className="error-message">❌ {uploadError}</div>}

            {uploadCompleted ? (
              <div className="upload-completion">
                <div className="success-icon">✅</div>
                <h3>Review Complete!</h3>
                <p>Your manuscript analysis is ready.</p>
                <div className="action-buttons">
                  <button className="btn-view" onClick={handleViewReview}>
                    👁️ View Review
                  </button>
                  <button className="btn-download-review" onClick={handleDownloadReview}>
                    📥 Download Review
                  </button>
                </div>
                <button className="btn-new-upload" onClick={handleNewUpload}>
                  📄 Upload Another Document
                </button>
              </div>
            ) : uploadProcessing ? (
              <div className="upload-processing">
                <div className="spinner-small"></div>
                <p>📊 Review in progress...</p>
                <p className="processing-note">This typically takes 2-5 minutes. Please wait...</p>
              </div>
            ) : (
              <button
                className="btn-upload"
                onClick={handleUpload}
                disabled={uploading || !file}
              >
                {uploading ? (
                  <>
                    <div className="spinner-small"></div>
                    Uploading...
                  </>
                ) : (
                  '🚀 Start Review'
                )}
              </button>
            )}

            <div className="upload-info">
              <h4>What happens next?</h4>
              <ul>
                <li>🔬 Methodology analysis by AI agents</li>
                <li>📚 Literature review and citation check</li>
                <li>✍️ Clarity and writing quality assessment</li>
                <li>⚖️ Ethics and compliance evaluation</li>
                <li>📊 Comprehensive final report generation</li>
              </ul>
              <p className="info-note">Average processing time: 2-5 minutes</p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'overview' && (
        <div className="overview-tab">
          <div className="stats-grid">
            <div className="stat-card">
              <h3>Total Submissions</h3>
              <p className="stat-value">{stats?.total_submissions || 0}</p>
            </div>
            <div className="stat-card success">
              <h3>Completed Reviews</h3>
              <p className="stat-value">{stats?.completed_reviews || 0}</p>
            </div>
            <div className="stat-card warning">
              <h3>In Progress</h3>
              <p className="stat-value">{stats?.in_progress || 0}</p>
            </div>
            <div className="stat-card danger">
              <h3>Failed Reviews</h3>
              <p className="stat-value">{stats?.failed_reviews || 0}</p>
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
              </div>
            </div>
          )}

          <div className="recent-submissions">
            <h3>Recent Submissions</h3>
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {submissions.slice(0, 5).map(sub => (
                  <tr key={sub._id}>
                    <td>{sub.title}</td>
                    <td>{sub.detected_domain || 'Unknown'}</td>
                    <td><span className={`status-badge ${sub.status}`}>{sub.status}</span></td>
                    <td>{formatDate(sub.created_at)}</td>
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
              <option value="completed">Completed</option>
              <option value="processing">Processing</option>
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
                    <p><strong>Domain:</strong> {sub.detected_domain || 'Unknown'}</p>
                    <p><strong>Submitted:</strong> {formatDate(sub.created_at)}</p>
                    {sub.completed_at && <p><strong>Completed:</strong> {formatDate(sub.completed_at)}</p>}
                  </div>
                  <div className="submission-actions">
                    <button
                      onClick={() => downloadFile(`/api/v1/downloads/manuscripts/${sub._id}`, sub.title)}
                      className="btn-download"
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
                        className="btn-download"
                        title="Download review PDF"
                      >
                        📋 Review
                      </button>
                    )}
                    <button onClick={() => handleDeleteSubmission(sub._id)} className="btn-delete">Delete</button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {activeTab === 'analytics' && (
        <div className="analytics-tab">
          <div className="analytics-section">
            <h3>Submission Timeline (Last 30 Days)</h3>
            <div className="timeline-chart">
              {timeline.length > 0 ? (
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Total</th>
                      <th>Completed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {timeline.map(item => (
                      <tr key={item._id}>
                        <td>{item._id}</td>
                        <td>{item.count}</td>
                        <td>{item.completed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No submissions in the last 30 days</p>
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
    </div>
  );
};

export default AuthorDashboard;
