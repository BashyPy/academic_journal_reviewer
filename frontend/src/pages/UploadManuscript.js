import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from '../services/axiosConfig';
import rateLimiter from '../services/rateLimiter';
import authService from '../services/authService';
import './UploadManuscript.css';

const UploadManuscript = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [submissionId, setSubmissionId] = useState(null);
  const [report, setReport] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const navigate = useNavigate();
  const user = authService.getUser();

  const handleFileChange = (selectedFile) => {
    if (selectedFile) {
      const fileExt = selectedFile.name.split('.').pop().toLowerCase();
      if (!['pdf', 'docx'].includes(fileExt)) {
        setError('Only PDF and DOCX files are allowed');
        setFile(null);
        return;
      }
      setError('');
      setFile(selectedFile);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (!processing) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await rateLimiter.makeRequest('upload', () =>
        axios.post('/api/v1/submissions/upload', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      );
      setSubmissionId(response.data.submission_id);
      setProcessing(true);
      setFile(null);
      pollForCompletion(response.data.submission_id);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Network error occurred');
    } finally {
      setUploading(false);
    }
  };

  const pollForCompletion = async (id) => {
    const interval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/submissions/${id}/report`);
        if (response.data.status === 'completed') {
          clearInterval(interval);
          setReport(response.data);
          setProcessing(false);
          setShowPreview(true);
        }
      } catch (err) {
        if (err.response?.status !== 400) {
          clearInterval(interval);
          setError('Failed to fetch report');
          setProcessing(false);
        }
      }
    }, 5000);
  };

  const downloadPDF = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${submissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      let baseTitle = report.title;
      if (baseTitle.includes('.')) {
        baseTitle = baseTitle.substring(0, baseTitle.lastIndexOf('.'));
      }
      link.setAttribute('download', `${baseTitle}_reviewed.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Download failed');
    }
  };

  const renderMarkdown = (text) => {
    if (!text) return null;
    return text.split('\n').map((line, i) => {
      if (line.startsWith('# ')) return <h1 key={i}>{line.slice(2)}</h1>;
      if (line.startsWith('## ')) return <h2 key={i}>{line.slice(3)}</h2>;
      if (line.startsWith('- ')) return <li key={i}>{line.slice(2)}</li>;
      if (line.trim() === '') return <br key={i} />;
      return <p key={i}>{line}</p>;
    });
  };

  return (
    <div className="upload-page">
      <div className="page-header">
        <div>
          <h1>📄 Upload Manuscript</h1>
          <p>Submit your academic manuscript for AI-powered review</p>
        </div>
        <div className="header-actions">
          <button onClick={() => navigate('/author-dashboard')} className="btn-secondary">
            ← Back to Dashboard
          </button>
          {user && <span className="user-badge">👤 {user.name}</span>}
        </div>
      </div>

      {!showPreview ? (
        <div className="upload-section">
          <div className="upload-card">
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
                <p className="drop-subtitle">Supported formats: PDF, DOCX</p>
                <p className="drop-subtitle">Maximum size: 50MB</p>
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

            {error && <div className="error-message">❌ {error}</div>}

            {processing ? (
              <div className="processing-status">
                <div className="spinner"></div>
                <h3>🔄 Review in Progress</h3>
                <p>Your manuscript is being analyzed by our AI agents...</p>
                <div className="progress-steps">
                  <div className="step">🔬 Methodology analysis</div>
                  <div className="step">📚 Literature review</div>
                  <div className="step">✍️ Clarity assessment</div>
                  <div className="step">⚖️ Ethics evaluation</div>
                  <div className="step">🧠 Final synthesis</div>
                </div>
              </div>
            ) : (
              <button
                className="btn-primary"
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
          </div>
        </div>
      ) : (
        <div className="preview-section">
          <div className="completion-banner">
            <div className="success-icon">✅</div>
            <h2>Review Complete!</h2>
            <p>Your manuscript analysis is ready.</p>
            <div className="action-buttons">
              <button onClick={() => window.open(`/review/${submissionId}`, '_blank')} className="btn-view">
                👁️ View Review
              </button>
              <button onClick={downloadPDF} className="btn-download">
                📥 Download Review
              </button>
            </div>
            <button onClick={() => { setShowPreview(false); setReport(null); setSubmissionId(null); }} className="btn-new-upload">
              📄 Upload Another Document
            </button>
          </div>

          <div className="preview-header">
            <h3>📄 Preview</h3>
          </div>

          <div className="preview-card">
            <div className="preview-meta">
              <h4>{report.title}</h4>
              {report.completed_at && (
                <p className="completion-date">
                  ✅ Completed: {new Date(report.completed_at).toLocaleDateString()}
                </p>
              )}
            </div>

            <div className="preview-content">
              {renderMarkdown(report.final_report?.substring(0, 1000))}
              {report.final_report?.length > 1000 && (
                <p className="preview-note">... (Preview truncated. Click "View Review" to see the full report)</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UploadManuscript;
