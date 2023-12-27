// MeetingMinutes.js

import React from 'react';
import './MeetingMinutes.css';

const MeetingMinutes = ({ minutes }) => {
  return (
    <div className="meeting-minutes-container">
      <h2 className="meeting-minutes-title">Meeting Minutes</h2>
      <div className="meeting-minutes-content">
        {Object.entries(minutes).map(([key, value]) => (
          <div key={key} className="meeting-minutes-section">
            <h3 className="meeting-minutes-section-title">{key}</h3>
            <p className="meeting-minutes-section-text">{value}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MeetingMinutes;

