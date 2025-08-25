import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import './App.css';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m here to help you learn more about [Your Name]. Feel free to ask me about their experience, skills, projects, or anything else you\'d like to know!',
      timestamp: new Date()
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => uuidv4());
  const [recruiterInfo, setRecruiterInfo] = useState({
    name: '',
    company: '',
    email: ''
  });
  const [showRecruiterForm, setShowRecruiterForm] = useState(true);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/chat`, {
        message: inputMessage,
        session_id: sessionId,
        recruiter_info: recruiterInfo
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleRecruiterInfoSubmit = (e) => {
    e.preventDefault();
    setShowRecruiterForm(false);
  };

  if (showRecruiterForm) {
    return (
      <div className="app">
        <div className="recruiter-form-container">
          <div className="recruiter-form">
            <h2>Welcome, Recruiter!</h2>
            <p>Please introduce yourself before we begin chatting about the candidate.</p>
            <form onSubmit={handleRecruiterInfoSubmit}>
              <div className="form-group">
                <label htmlFor="name">Your Name:</label>
                <input
                  type="text"
                  id="name"
                  value={recruiterInfo.name}
                  onChange={(e) => setRecruiterInfo(prev => ({ ...prev, name: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="company">Company:</label>
                <input
                  type="text"
                  id="company"
                  value={recruiterInfo.company}
                  onChange={(e) => setRecruiterInfo(prev => ({ ...prev, company: e.target.value }))}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="email">Email:</label>
                <input
                  type="email"
                  id="email"
                  value={recruiterInfo.email}
                  onChange={(e) => setRecruiterInfo(prev => ({ ...prev, email: e.target.value }))}
                  required
                />
              </div>
              <button type="submit" className="submit-btn">Start Chat</button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="chat-header">
        <h1>Chat with [Your Name]'s AI Assistant</h1>
        <p>Hello {recruiterInfo.name} from {recruiterInfo.company}! Ask me anything about the candidate.</p>
      </header>
      
      <div className="chat-container">
        <div className="messages">
          {messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">
                {message.content}
              </div>
              <div className="message-time">
                {message.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="message assistant">
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <form onSubmit={handleSendMessage} className="message-form">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask about experience, skills, projects..."
            disabled={isLoading}
            autoFocus
          />
          <button type="submit" disabled={isLoading || !inputMessage.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
