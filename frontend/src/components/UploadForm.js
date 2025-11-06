import React, { useState, useEffect } from 'react';
import axios from '../services/axiosConfig';
import rateLimiter from '../services/rateLimiter';

const UploadForm = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [submissionId, setSubmissionId] = useState(null);
  const [submissionData, setSubmissionData] = useState(null);
  const [error, setError] = useState('');
  const [dragOver, setDragOver] = useState(false);

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

  const handleInputChange = (e) => {
    if (!processing) {
      handleFileChange(e.target.files[0]);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (!processing) {
      const droppedFile = e.dataTransfer.files[0];
      handleFileChange(droppedFile);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  useEffect(() => {
    let interval;
    if (processing && submissionId) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`/api/v1/submissions/${submissionId}/report`);
          if (!response.data.processing) {
            setProcessing(false);
            setCompleted(true);
            setSubmissionData(response.data);
            clearInterval(interval);
          }
        } catch (err) {
          console.error('Status check error:', err);
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [processing, submissionId]);

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
      const subId = response.data.submission_id;
      setSubmissionId(subId);
      onUploadSuccess(subId);
      setProcessing(true);
      setFile(null);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Network error occurred');
    } finally {
      setUploading(false);
    }
  };

  const handleViewReview = () => {
    window.open(`/review/${submissionId}`, '_blank');
  };

  const handleDownloadReview = async () => {
    try {
      const response = await axios.get(`/api/v1/submissions/${submissionId}/download`, {
        responseType: 'blob'
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const baseName = submissionData?.title?.replace(/\.[^/.]+$/, '') || 'review';
      link.setAttribute('download', `${baseName}_reviewed.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
      setError('Failed to download review');
    }
  };

  const handleNewUpload = () => {
    setCompleted(false);
    setProcessing(false);
    setSubmissionId(null);
    setSubmissionData(null);
    setFile(null);
    setError('');
  };

  return (
    <div className="upload-form">
      <h2>📄 Upload Academic Manuscript</h2>
      <p>Upload your PDF or DOCX file for comprehensive AI-powered review</p>

      <div
        className={`file-drop-zone ${dragOver ? 'dragover' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('file-input').click()}
      >
        <div>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📁</div>
          <p><strong>Drop your file here or click to browse</strong></p>
          <p>Supported formats: PDF, DOCX</p>
          <p>Maximum size: 50MB</p>
        </div>
      </div>

      <div className="file-input">
        <input
          id="file-input"
          type="file"
          onChange={handleInputChange}
          accept=".pdf,.docx"
        />
        <label htmlFor="file-input">
          📎 Choose File
        </label>
      </div>

      {file && (
        <div className="selected-file">
          <strong>Selected:</strong> {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
        </div>
      )}

      {error && <div className="error">❌ {error}</div>}

      {completed ? (
        <div className="completion-message">
          <div className="success-icon">✅</div>
          <h3>Review Complete!</h3>
          <p>Your manuscript analysis is ready.</p>
          <div className="action-buttons">
            <button className="view-button" onClick={handleViewReview}>
              👁️ View Review
            </button>
            <button className="download-button" onClick={handleDownloadReview}>
              📥 Download Review
            </button>
          </div>
          <button className="new-upload-button" onClick={handleNewUpload}>
            📄 Upload Another Document
          </button>
        </div>
      ) : processing ? (
        <div className="processing-message">
          <div className="loading-spinner"></div>
          <p>📊 Review in progress...</p>
          <p>This typically takes 2-5 minutes. Please wait...</p>
        </div>
      ) : (
        <button
          className="upload-button"
          onClick={handleUpload}
          disabled={uploading || !file}
        >
          {uploading ? (
            <>
              <div className="loading-spinner" style={{ width: '20px', height: '20px', display: 'inline-block', marginRight: '10px' }}></div>
              Uploading...
            </>
          ) : (
            '🚀 Start Review'
          )}
        </button>
      )}
    </div>
  );
};

export default UploadForm;
