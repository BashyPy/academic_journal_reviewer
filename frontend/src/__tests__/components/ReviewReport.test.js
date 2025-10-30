import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import axios from 'axios';
import ReviewReport from '../../components/ReviewReport';

jest.mock('axios');
const mockedAxios = axios;

describe('ReviewReport Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders loading state initially', () => {
    mockedAxios.get.mockImplementationOnce(() => new Promise(() => {}));
    
    render(<ReviewReport submissionId="test-id" />);
    
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('displays final report', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        title: 'test.pdf',
        final_report: '# Executive Summary\n\nOverall Score: 8.5/10\n\n## Methodology\nStrong methodology with clear design.',
        completed_at: '2024-01-15T10:30:00Z',
        status: 'completed',
        disclaimer: 'This is an AI-generated review.'
      }
    });

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/final review report/i)).toBeInTheDocument();
      expect(screen.getByText(/test.pdf/i)).toBeInTheDocument();
      expect(screen.getByText(/executive summary/i)).toBeInTheDocument();
      expect(screen.getByText(/overall score: 8.5\/10/i)).toBeInTheDocument();
      expect(screen.getByText('Strong methodology with clear design.')).toBeInTheDocument();
    });
  });

  test('shows disclaimer', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        title: 'test.pdf',
        final_report: 'Report content',
        disclaimer: 'This is an AI-generated review requiring human validation.'
      }
    });

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/disclaimer/i)).toBeInTheDocument();
      expect(screen.getByText(/ai-generated review requiring human validation/i)).toBeInTheDocument();
    });
  });

  test('handles report not ready', async () => {
    mockedAxios.get.mockRejectedValueOnce({
      response: {
        status: 400,
        data: { detail: 'Review not completed yet' }
      }
    });

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/review not completed/i)).toBeInTheDocument();
      expect(screen.getByText(/please wait/i)).toBeInTheDocument();
    });
  });

  test('handles API error', async () => {
    mockedAxios.get.mockRejectedValueOnce({
      response: {
        data: { detail: 'Submission not found' }
      }
    });

    render(<ReviewReport submissionId="invalid-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/error/i)).toBeInTheDocument();
      expect(screen.getByText(/submission not found/i)).toBeInTheDocument();
    });
  });

  test('download PDF functionality', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        title: 'test.pdf',
        final_report: 'Report content',
        status: 'completed'
      }
    });

    // Mock PDF download
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    mockedAxios.get.mockResolvedValueOnce({
      data: mockBlob,
      headers: { 'content-type': 'application/pdf' }
    });

    // Mock URL.createObjectURL
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/download pdf/i)).toBeInTheDocument();
    });

    const downloadButton = screen.getByText(/download pdf/i);
    fireEvent.click(downloadButton);

    await waitFor(() => {
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/v1/submissions/test-id/download',
        expect.objectContaining({ responseType: 'blob' })
      );
    });
  });

  test('formats completion date', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        title: 'test.pdf',
        final_report: 'Report content',
        completed_at: '2024-01-15T10:30:00Z',
        status: 'completed'
      }
    });

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText(/completed on/i)).toBeInTheDocument();
      expect(screen.getByText(/january 15, 2024/i)).toBeInTheDocument();
    });
  });

  test('renders markdown content', async () => {
    mockedAxios.get.mockResolvedValueOnce({
      data: {
        submission_id: 'test-id',
        title: 'test.pdf',
        final_report: '# Main Title\n\n## Subtitle\n\n**Bold text** and *italic text*\n\n- List item 1\n- List item 2',
        status: 'completed'
      }
    });

    render(<ReviewReport submissionId="test-id" />);
    
    await waitFor(() => {
      expect(screen.getByText('Main Title')).toBeInTheDocument();
      expect(screen.getByText('Subtitle')).toBeInTheDocument();
      expect(screen.getByText('Bold text')).toBeInTheDocument();
      expect(screen.getByText('List item 1')).toBeInTheDocument();
    });
  });
});