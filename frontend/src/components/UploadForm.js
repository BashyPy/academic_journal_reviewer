import React, { useState } from 'react';
import axios from 'axios';

const UploadForm = ({ onUploadSuccess }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
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
    handleFileChange(e.target.files[0]);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    handleFileChange(droppedFile);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
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
      const response = await axios.post('/api/v1/submissions/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onUploadSuccess(response.data.submission_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Network error occurred');
    } finally {
      setUploading(false);
    }
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
      
      <button 
        className="upload-button" 
        onClick={handleUpload} 
        disabled={uploading || !file}
      >
        {uploading ? (
          <>
            <div className="loading-spinner" style={{ width: '20px', height: '20px', display: 'inline-block', marginRight: '10px' }}></div>
            Processing...
          </>
        ) : (
          '🚀 Start Review'
        )}
      </button>
    </div>
  );
};

export default UploadForm;