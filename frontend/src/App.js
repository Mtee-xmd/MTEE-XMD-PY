import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Session Manager Component
const SessionManager = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await axios.get(`${API}/sessions`);
      setSessions(response.data.sessions || []);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const response = await axios.post(`${API}/sessions/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      if (response.data.success) {
        alert('Session file uploaded successfully!');
        setSelectedFile(null);
        document.getElementById('file-input').value = '';
        fetchSessions();
      }
    } catch (error) {
      alert(`Upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (fileId, filename) => {
    try {
      const response = await axios.get(`${API}/sessions/download/${fileId}`);
      if (response.data.success) {
        alert(`Session downloaded: ${filename}`);
      }
    } catch (error) {
      alert(`Download failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDelete = async (fileId, filename) => {
    if (!window.confirm(`Delete session file: ${filename}?`)) return;

    try {
      const response = await axios.delete(`${API}/sessions/${fileId}`);
      if (response.data.success) {
        alert('Session file deleted successfully');
        fetchSessions();
      }
    } catch (error) {
      alert(`Delete failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  const restoreLatestSession = async () => {
    try {
      const response = await axios.post(`${API}/bot/restore-session`);
      if (response.data.success) {
        alert(`Session restored: ${response.data.filename}`);
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      alert(`Restore failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">Session Manager</h2>
      
      {/* Upload Section */}
      <div className="mb-8 p-4 bg-gray-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Upload Session File</h3>
        <div className="flex items-center space-x-4">
          <input
            id="file-input"
            type="file"
            onChange={(e) => setSelectedFile(e.target.files[0])}
            accept=".json,.wa,.session"
            className="flex-1 p-2 border border-gray-300 rounded"
          />
          <button
            onClick={handleFileUpload}
            disabled={!selectedFile || uploading}
            className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-gray-400"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>

      {/* Restore Section */}
      <div className="mb-8 p-4 bg-green-50 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Session Restoration</h3>
        <button
          onClick={restoreLatestSession}
          className="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Restore Latest Session
        </button>
        <p className="text-sm text-gray-600 mt-2">
          This will download and restore the most recent session from Mega.nz
        </p>
      </div>

      {/* Sessions List */}
      <div>
        <h3 className="text-lg font-semibold mb-4">Stored Sessions ({sessions.length})</h3>
        
        {sessions.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No session files found</p>
        ) : (
          <div className="space-y-4">
            {sessions.map((session) => (
              <div key={session.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-gray-800">{session.filename}</h4>
                    <p className="text-sm text-gray-500">
                      Size: {(session.file_size / 1024).toFixed(2)} KB
                    </p>
                    <p className="text-sm text-gray-500">
                      Uploaded: {new Date(session.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex space-x-2">
                    <a
                      href={session.mega_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-1 bg-gray-500 text-white text-sm rounded hover:bg-gray-600"
                    >
                      View in Mega
                    </a>
                    <button
                      onClick={() => handleDownload(session.mega_file_id, session.filename)}
                      className="px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600"
                    >
                      Download
                    </button>
                    <button
                      onClick={() => handleDelete(session.mega_file_id, session.filename)}
                      className="px-3 py-1 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// Bot Status Component
const BotStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000); // Update every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const response = await axios.get(`${API}/bot/status`);
      setStatus(response.data);
    } catch (error) {
      console.error('Failed to fetch bot status:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateQR = async () => {
    try {
      const response = await axios.post(`${API}/bot/generate-qr`);
      if (response.data.success) {
        fetchStatus();
      }
    } catch (error) {
      alert(`Failed to generate QR: ${error.response?.data?.detail || error.message}`);
    }
  };

  const simulateConnection = async () => {
    try {
      const response = await axios.post(`${API}/bot/connect`);
      if (response.data.success) {
        alert('WhatsApp connected successfully!');
        fetchStatus();
      }
    } catch (error) {
      alert(`Connection failed: ${error.response?.data?.detail || error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-500"></div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">WhatsApp Bot Status</h2>
      
      <div className="space-y-4">
        {/* Connection Status */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <span className="font-medium">Connection Status:</span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            status?.is_connected 
              ? 'bg-green-100 text-green-800' 
              : 'bg-red-100 text-red-800'
          }`}>
            {status?.is_connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        {/* Phone Number */}
        {status?.phone_number && (
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <span className="font-medium">Phone Number:</span>
            <span className="text-gray-700">{status.phone_number}</span>
          </div>
        )}

        {/* Session Status */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <span className="font-medium">Session Restored:</span>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            status?.session_restored 
              ? 'bg-blue-100 text-blue-800' 
              : 'bg-yellow-100 text-yellow-800'
          }`}>
            {status?.session_restored ? 'Yes' : 'No'}
          </span>
        </div>

        {/* Last Seen */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <span className="font-medium">Last Seen:</span>
          <span className="text-gray-700">
            {status?.last_seen ? new Date(status.last_seen).toLocaleString() : 'Never'}
          </span>
        </div>

        {/* QR Code Section */}
        {status?.qr_code && !status?.is_connected && (
          <div className="p-4 bg-yellow-50 rounded-lg">
            <h3 className="font-medium mb-2">QR Code for Authentication:</h3>
            <div className="bg-white p-4 rounded border text-center">
              <code className="text-sm text-gray-600">{status.qr_code}</code>
            </div>
            <p className="text-sm text-gray-600 mt-2">
              Scan this QR code with WhatsApp to connect
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex space-x-4 pt-4">
          {!status?.is_connected && (
            <button
              onClick={generateQR}
              className="px-6 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Generate QR Code
            </button>
          )}
          
          {status?.qr_code && !status?.is_connected && (
            <button
              onClick={simulateConnection}
              className="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Simulate Connection
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  const [activeTab, setActiveTab] = useState('status');

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">
              WhatsApp Bot with Secure Session Storage
            </h1>
            <p className="text-gray-600">
              Manage your WhatsApp bot sessions with secure local storage
            </p>
          </div>

          {/* Navigation */}
          <div className="flex justify-center mb-8">
            <div className="bg-white rounded-lg p-1 shadow-md">
              <button
                onClick={() => setActiveTab('status')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'status'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-blue-500'
                }`}
              >
                Bot Status
              </button>
              <button
                onClick={() => setActiveTab('sessions')}
                className={`px-6 py-2 rounded-md font-medium transition-colors ${
                  activeTab === 'sessions'
                    ? 'bg-blue-500 text-white'
                    : 'text-gray-600 hover:text-blue-500'
                }`}
              >
                Session Manager
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="max-w-4xl mx-auto">
            {activeTab === 'status' && <BotStatus />}
            {activeTab === 'sessions' && <SessionManager />}
          </div>

          {/* Footer */}
          <div className="text-center mt-12 text-gray-500">
            <p>WhatsApp Bot with Mega.nz Storage - Secure session management</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;