import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import UploadForm from '../../components/UploadForm';

jest.mock('axios');
const mockedAxios = axios;

describe('UploadForm Component', () => {
  const mockOnUploadSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders upload form elements', () => {
    render(<UploadForm onUploadSuccess={mockOnUploadSuccess} />);
    
    expect(screen.getByText(/upload manuscript/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/select file/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload/i })).toBeInTheDocument();
  });

  test('shows file validation message for invalid file type', () => {
    render(<UploadForm onUploadSuccess={mockOnUploadSuccess} />);
    
    const fileInput = screen.getByLabelText(/select file/i);
    const invalidFile = new File(['content'], 'test.txt', { type: 'text/plain' });
    
    fireEvent.change(fileInput, { target: { files: [invalidFile] } });
    
    expect(screen.getByText(/only pdf and docx files are allowed/i)).toBeInTheDocument();
  });

  test('successful file upload', async () => {
    mockedAxios.post.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id-123',
        status: 'processing',
        message: 'Upload successful'
      }
    });

    render(<UploadForm onUploadSuccess={mockOnUploadSuccess} />);
    
    const fileInput = screen.getByLabelText(/select file/i);
    const uploadButton = screen.getByRole('button', { name: /upload/i });
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    fireEvent.click(uploadButton);
    
    await waitFor(() => {
      expect(mockOnUploadSuccess).toHaveBeenCalledWith('test-id-123');
    });
  });

  test('handles upload error', async () => {
    mockedAxios.post.mockRejectedValueOnce({
      response: {
        data: { detail: 'File too large' }
      }
    });

    render(<UploadForm onUploadSuccess={mockOnUploadSuccess} />);
    
    const fileInput = screen.getByLabelText(/select file/i);
    const uploadButton = screen.getByRole('button', { name: /upload/i });
    const validFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    
    fireEvent.change(fileInput, { target: { files: [validFile] } });
    fireEvent.click(uploadButton);
    
    await waitFor(() => {
      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });
  });
});