import React from 'react';
import { useParams } from 'react-router-dom';
import ReviewReport from '../components/ReviewReport';
import './ReviewPage.css';

const ReviewPage = () => {
  const { submissionId } = useParams();

  return (
    <div className="review-page">
      <div className="review-page-header">
        <h1>📋 Manuscript Review Report</h1>
      </div>
      <ReviewReport submissionId={submissionId} />
    </div>
  );
};

export default ReviewPage;
