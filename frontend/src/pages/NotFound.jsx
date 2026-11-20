import React from 'react';
import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="full-screen-center">
      <div className="error-card">
        <span className="error-card__icon">🔍</span>
        <h1 className="error-card__title">404 - Page Not Found</h1>
        <p className="error-card__message">
          The requested page does not exist or has been moved.
        </p>
        <Link to="/dashboard" className="btn btn--primary">
          Return to Dashboard
        </Link>
      </div>
    </div>
  );
}
