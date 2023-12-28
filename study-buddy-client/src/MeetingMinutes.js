import React from 'react';
import './MeetingMinutes.css';

const MeetingMinutes = ({ minutes }) => {
  return (
    <div className="meeting-minutes-container">
      <div className="meeting-minutes-content">
        {Object.entries(minutes).map(([sectionTitle, sectionText], index) => (
          <div className="meeting-minutes-section" key={index}>
            <h2 className="meeting-minutes-section-title">{sectionTitle}</h2>
            <p className="meeting-minutes-section-text">{sectionText}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MeetingMinutes;

