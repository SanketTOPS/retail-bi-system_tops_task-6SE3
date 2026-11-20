import React from 'react';
import { Link } from 'react-router-dom';

export default function Unauthorized() {
  return (
    <div className="full-screen-center">
      <div className="error-card">
        <span className="error-card__icon">🚫</span>
        <h1 className="error-card__title">403 - Access Denied</h1>
        <p className="error-card__message">
          You do not have the required permissions to view this resource.
        </p>
        <Link to="/dashboard" className="btn btn--primary">
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
