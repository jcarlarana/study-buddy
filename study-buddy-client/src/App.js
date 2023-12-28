import React, { useState } from 'react';
import axios from 'axios';
import MeetingMinutes from './MeetingMinutes';
import './App.css';

const App = () => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [meetingMinutes, setMeetingMinutes] = useState(null);

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
  };

  const handleGenerate = async () => {
    try {
      setStatus('Transcribing...');
      const transcribeResponse = await transcribeAudio();
      const transcription = transcribeResponse.data.transcription;

      setStatus('Generating Minutes...');
      const minutesResponse = await generateMeetingMinutes(transcription);
      const minutes = minutesResponse.data;

      setMeetingMinutes(minutes);
      setStatus('Process Completed!');
    } catch (error) {
      console.error('Error during process:', error);
      setStatus('Error Occurred');
    }
  };

  const transcribeAudio = async () => {
    const formData = new FormData();
    formData.append('audio', file);

    return axios.post('http://localhost:5000/transcribe', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  };

  const generateMeetingMinutes = async (transcription) => {
    try {
      const formData = new FormData();
      formData.append('transcription', transcription);

      return axios.post('http://localhost:5000/meeting-minutes', formData);
    } catch (error) {
      console.error('Error during meeting minutes generation:', error);
      throw error; // Rethrow the error to be caught by the caller
    }
  };

  const handleDownloadPdf = async () => {
    try {
      const pdfResponse = null;
      const pdfUrl = pdfResponse.data.url;
      window.open(pdfUrl, '_blank');
    } catch (error) {
      console.error('Error during download PDF:', error);
    }
  };

  return (
    <div className="app-container">
      <input type="file" accept="audio/*" onChange={handleFileChange} />

      <button className="generate-button" onClick={handleGenerate}>
        Generate
      </button>

      {/* Display status */}
      {status && <p className="status">{status}</p>}

      {/* Display Meeting Minutes */}
      {meetingMinutes && <MeetingMinutes minutes={meetingMinutes} />}

    </div>
  );
};

export default App;

