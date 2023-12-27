import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('');
  const [pdfUrl, setPdfUrl] = useState('');

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

      setStatus('Saving PDF...');
      const pdfResponse = await saveAsPdf(minutes);
      const pdfUrl = pdfResponse.data.pdfUrl;

      setStatus('Process Completed!');
      setPdfUrl(pdfUrl);
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
    const formData = new FormData();
    formData.append('transcription', transcription);

    return axios.post('http://localhost:5000/meeting-minutes', formData);
  };

  const saveAsPdf = async (minutes) => {
    const data = {
      filename: 'output/meeting_minutes.pdf',
      minutes: minutes,
    };
  
    return axios.post('http://localhost:5000/save-as-pdf', data, {
      headers: { 'Content-Type': 'application/json' },
    });
  };

  return (
    <div className="app-container">
      <input type="file" accept="audio/*" onChange={handleFileChange} />

      <button className="generate-button" onClick={handleGenerate}>
        Generate
      </button>

      {/* Display status */}
      {status && <p className="status">{status}</p>}

      {/* Display PDF */}
      {pdfUrl && (
        <iframe title="Generated PDF" src={pdfUrl} className="pdf-iframe" width="600" height="400"></iframe>
      )}
    </div>
  );
};

export default App;

