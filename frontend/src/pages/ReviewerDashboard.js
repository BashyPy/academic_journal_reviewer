import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import authService from '../services/authService';
import UploadForm from '../components/UploadForm';
import './ReviewerDashboard.css';

const ReviewerDashboard = () => {
  const navigate = useNavigate();
  const user = authService.getUser();
  const [activeTab, setActiveTab] = useState('overview');
  const [stats, setStats] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [reviewForm, setReviewForm] = useState({
    methodology_score: 5,
    literature_score: 5,
    clarity_score: 5,
    ethics_score: 5,
    overall_score: 5,
    strengths: '',
    weaknesses: '',
    comments: '',
    recommendation: 'revise'
  });
  const [timeline, setTimeline] = useState([]);
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const [statsRes, assignmentsRes, timelineRes, domainsRes] = await Promise.all([
        axios.get('/api/v1/reviewer/dashboard/stats'),
        axios.get('/api/v1/reviewer/assignments'),
        axios.get('/api/v1/reviewer/analytics/timeline'),
        axios.get('/api/v1/reviewer/analytics/domains')
      ]);

      setStats(statsRes.data);
      setAssignments(assignmentsRes.data.assignments);
      setTimeline(timelineRes.data.timeline);
      setDomains(domainsRes.data.domains);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      alert('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const handleStartReview = async (assignmentId) => {
    try {
      await axios.post(`/api/v1/reviewer/assignments/${assignmentId}/start`);
      alert('Review started successfully');
      fetchDashboardData();
    } catch (error) {
      console.error('Error starting review:', error);
      alert('Failed to start review');
    }
  };

  const handleViewAssignment = async (assignmentId) => {
    try {
      const response = await axios.get(`/api/v1/reviewer/assignments/${assignmentId}`);
      setSelectedAssignment(response.data);
      setActiveTab('review-form');
    } catch (error) {
      console.error('Error fetching assignment:', error);
      alert('Failed to load assignment details');
    }
  };

  const handleSubmitReview = async () => {
    if (!selectedAssignment) return;

    try {
      await axios.post(
        `/api/v1/reviewer/assignments/${selectedAssignment._id}/submit`,
        reviewForm
      );
      alert('Review submitted successfully');
      setSelectedAssignment(null);
      setActiveTab('assignments');
      fetchDashboardData();
    } catch (error) {
      console.error('Error submitting review:', error);
      alert('Failed to submit review');
    }
  };

  const filteredAssignments = statusFilter === 'all'
    ? assignments
    : assignments.filter(a => a.status === statusFilter);

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

  if (loading) {
    return <div className="reviewer-dashboard loading">Loading dashboard...</div>;
  }

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="reviewer-dashboard">
      <header className="dashboard-header">
        <div>
          <h1>Reviewer Dashboard</h1>
          <p>Manage your manuscript review assignments</p>
        </div>
        <div className="user-info">
          <span>👤 {user?.name || user?.email}</span>
          <button onClick={handleLogout} className="btn-logout">Logout</button>
        </div>
      </header>

      <nav className="dashboard-tabs">
        <button
          className={activeTab === 'overview' ? 'active' : ''}
          onClick={() => setActiveTab('overview')}
        >
          Overview
        </button>
        <button
          className={activeTab === 'upload' ? 'active' : ''}
          onClick={() => setActiveTab('upload')}
        >
          📤 Upload
        </button>
        <button
          className={activeTab === 'assignments' ? 'active' : ''}
          onClick={() => setActiveTab('assignments')}
        >
          My Assignments
        </button>
        <button
          className={activeTab === 'analytics' ? 'active' : ''}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </nav>

      <div className="dashboard-content">
        {activeTab === 'upload' && (
          <div className="upload-tab">
            <UploadForm onUploadSuccess={(id) => { alert(`Manuscript uploaded successfully! Submission ID: ${id}`); fetchDashboardData(); }} />
          </div>
        )}

        {activeTab === 'overview' && (
          <div className="overview-tab">
            <div className="stats-grid">
              <div className="stat-card">
                <h3>Total Assigned</h3>
                <p className="stat-value">{stats?.total_assigned || 0}</p>
              </div>
              <div className="stat-card pending">
                <h3>Pending Reviews</h3>
                <p className="stat-value">{stats?.pending_reviews || 0}</p>
              </div>
              <div className="stat-card in-progress">
                <h3>In Progress</h3>
                <p className="stat-value">{stats?.in_progress || 0}</p>
              </div>
              <div className="stat-card completed">
                <h3>Completed</h3>
                <p className="stat-value">{stats?.completed_reviews || 0}</p>
              </div>
              <div className="stat-card">
                <h3>Avg Review Time</h3>
                <p className="stat-value">{stats?.avg_review_time_hours || 0}h</p>
              </div>
            </div>

            <div className="recent-assignments">
              <h2>Recent Assignments</h2>
              <table className="assignments-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Domain</th>
                    <th>Status</th>
                    <th>Assigned</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {assignments.slice(0, 5).map(assignment => (
                    <tr key={assignment._id}>
                      <td>{assignment.submission_title}</td>
                      <td>{assignment.submission_domain}</td>
                      <td>
                        <span className={`status-badge ${assignment.status}`}>
                          {assignment.status}
                        </span>
                      </td>
                      <td>{new Date(assignment.assigned_at).toLocaleDateString()}</td>
                      <td>
                        <button
                          className="btn-download"
                          onClick={() => downloadFile(`/api/v1/downloads/manuscripts/${assignment.submission_id}`, assignment.submission_title)}
                          title="Download manuscript"
                        >
                          📄
                        </button>
                        {assignment.submission_status === 'completed' && (
                          <button
                            className="btn-download"
                            onClick={() => {
                              const baseName = assignment.submission_title.replace(/\.[^/.]+$/, '');
                              downloadFile(`/api/v1/downloads/reviews/${assignment.submission_id}`, `${baseName}_Reviewed.pdf`);
                            }}
                            title="Download review"
                          >
                            📋
                          </button>
                        )}
                        {assignment.status === 'pending' && (
                          <button
                            className="btn-start"
                            onClick={() => handleStartReview(assignment._id)}
                          >
                            Start
                          </button>
                        )}
                        {assignment.status === 'in_progress' && (
                          <button
                            className="btn-continue"
                            onClick={() => handleViewAssignment(assignment._id)}
                          >
                            Continue
                          </button>
                        )}
                        {assignment.status === 'completed' && (
                          <button
                            className="btn-view"
                            onClick={() => handleViewAssignment(assignment._id)}
                          >
                            View
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'assignments' && (
          <div className="assignments-tab">
            <div className="assignments-header">
              <h2>All Assignments</h2>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="status-filter"
              >
                <option value="all">All Status</option>
                <option value="pending">Pending</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
              </select>
            </div>

            <table className="assignments-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Domain</th>
                  <th>Status</th>
                  <th>Assigned</th>
                  <th>Due Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredAssignments.map(assignment => (
                  <tr key={assignment._id}>
                    <td>{assignment.submission_title}</td>
                    <td>{assignment.submission_domain}</td>
                    <td>
                      <span className={`status-badge ${assignment.status}`}>
                        {assignment.status}
                      </span>
                    </td>
                    <td>{new Date(assignment.assigned_at).toLocaleDateString()}</td>
                    <td>
                      {assignment.due_date
                        ? new Date(assignment.due_date).toLocaleDateString()
                        : 'N/A'}
                    </td>
                    <td>
                      <button
                        className="btn-download"
                        onClick={() => downloadFile(`/api/v1/downloads/manuscripts/${assignment.submission_id}`, assignment.submission_title)}
                        title="Download manuscript"
                      >
                        📄
                      </button>
                      {assignment.submission_status === 'completed' && (
                        <button
                          className="btn-download"
                          onClick={() => {
                            const baseName = assignment.submission_title.replace(/\.[^/.]+$/, '');
                            downloadFile(`/api/v1/downloads/reviews/${assignment.submission_id}`, `${baseName}_Reviewed.pdf`);
                          }}
                          title="Download review"
                        >
                          📋
                        </button>
                      )}
                      {assignment.status === 'pending' && (
                        <button
                          className="btn-start"
                          onClick={() => handleStartReview(assignment._id)}
                        >
                          Start
                        </button>
                      )}
                      {assignment.status === 'in_progress' && (
                        <button
                          className="btn-continue"
                          onClick={() => handleViewAssignment(assignment._id)}
                        >
                          Continue
                        </button>
                      )}
                      {assignment.status === 'completed' && (
                        <button
                          className="btn-view"
                          onClick={() => handleViewAssignment(assignment._id)}
                        >
                          View
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'review-form' && selectedAssignment && (
          <div className="review-form-tab">
            <h2>Review: {selectedAssignment.submission?.title}</h2>

            <div className="manuscript-preview">
              <h3>Manuscript Content</h3>
              <div className="content-preview">
                {selectedAssignment.submission?.content?.substring(0, 1000)}...
              </div>
            </div>

            <div className="review-form">
              <h3>Review Scores (1-10)</h3>

              <div className="score-input">
                <label>Methodology Score:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={reviewForm.methodology_score}
                  onChange={(e) => setReviewForm({...reviewForm, methodology_score: parseInt(e.target.value)})}
                />
              </div>

              <div className="score-input">
                <label>Literature Review Score:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={reviewForm.literature_score}
                  onChange={(e) => setReviewForm({...reviewForm, literature_score: parseInt(e.target.value)})}
                />
              </div>

              <div className="score-input">
                <label>Clarity Score:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={reviewForm.clarity_score}
                  onChange={(e) => setReviewForm({...reviewForm, clarity_score: parseInt(e.target.value)})}
                />
              </div>

              <div className="score-input">
                <label>Ethics Score:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={reviewForm.ethics_score}
                  onChange={(e) => setReviewForm({...reviewForm, ethics_score: parseInt(e.target.value)})}
                />
              </div>

              <div className="score-input">
                <label>Overall Score:</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={reviewForm.overall_score}
                  onChange={(e) => setReviewForm({...reviewForm, overall_score: parseInt(e.target.value)})}
                />
              </div>

              <div className="text-input">
                <label>Strengths:</label>
                <textarea
                  value={reviewForm.strengths}
                  onChange={(e) => setReviewForm({...reviewForm, strengths: e.target.value})}
                  rows="4"
                  placeholder="List the manuscript's strengths..."
                />
              </div>

              <div className="text-input">
                <label>Weaknesses:</label>
                <textarea
                  value={reviewForm.weaknesses}
                  onChange={(e) => setReviewForm({...reviewForm, weaknesses: e.target.value})}
                  rows="4"
                  placeholder="List areas for improvement..."
                />
              </div>

              <div className="text-input">
                <label>Detailed Comments:</label>
                <textarea
                  value={reviewForm.comments}
                  onChange={(e) => setReviewForm({...reviewForm, comments: e.target.value})}
                  rows="6"
                  placeholder="Provide detailed feedback..."
                />
              </div>

              <div className="recommendation-input">
                <label>Recommendation:</label>
                <select
                  value={reviewForm.recommendation}
                  onChange={(e) => setReviewForm({...reviewForm, recommendation: e.target.value})}
                >
                  <option value="accept">Accept</option>
                  <option value="revise">Minor Revisions</option>
                  <option value="major_revise">Major Revisions</option>
                  <option value="reject">Reject</option>
                </select>
              </div>

              <div className="form-actions">
                <button className="btn-cancel" onClick={() => setActiveTab('assignments')}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleSubmitReview}>
                  Submit Review
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="analytics-tab">
            <h2>Review Analytics</h2>

            <div className="analytics-section">
              <h3>Review Timeline (Last 30 Days)</h3>
              <div className="timeline-chart">
                {timeline.map(item => (
                  <div key={item._id} className="timeline-bar">
                    <span className="date">{item._id}</span>
                    <div className="bar" style={{width: `${item.count * 20}px`}}>
                      {item.count}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="analytics-section">
              <h3>Domain Distribution</h3>
              <div className="domain-chart">
                {domains.map(domain => (
                  <div key={domain._id} className="domain-bar">
                    <span className="domain-name">{domain._id}</span>
                    <div className="bar" style={{width: `${domain.count * 30}px`}}>
                      {domain.count}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ReviewerDashboard;
