import React, { useState } from 'react';
import axios from 'axios';

function UploadForm({ onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile && (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.docx'))) {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please select a PDF or DOCX file');
      setFile(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('/api/v1/submissions/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      onUploadSuccess(response.data.submission_id);
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-form">
      <h2>Upload Academic Manuscript</h2>
      <p>Upload your PDF or DOCX file for AI-powered review</p>
      
      <form onSubmit={handleSubmit}>
        <div className="file-input">
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileChange}
            disabled={uploading}
          />
        </div>
        
        {file && (
          <p>Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</p>
        )}
        
        {error && <div className="error">{error}</div>}
        
        <button
          type="submit"
          className="upload-button"
          disabled={!file || uploading}
        >
          {uploading ? 'Uploading...' : 'Start Review Process'}
        </button>
      </form>
    </div>
  );
}

export default UploadForm;