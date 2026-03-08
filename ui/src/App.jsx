import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000'; // Default FastAPI port

const initialMessages = [
  {
    id: 1,
    sender: 'HDFC Bot',
    text: "Hi! 👋 I'm your HDFC Mutual Fund guide. How can I help you today?",
    type: 'assistant',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    options: [
      "What is HDFC Mid Cap Fund's expense ratio?",
      "How to download account statement?",
      "What is the lock-in period for ELSS?"
    ]
  }
];

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const historyRef = useRef(null);

  useEffect(() => {
    // Scroll to bottom on new messages
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSend = async (text) => {
    const query = (text || input).strip ? (text || input).trim() : (text || input);
    if (!query) return;

    // Add user message
    const userMsg = {
      id: Date.now(),
      sender: 'You',
      text: query,
      type: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });

      if (!response.ok) throw new Error('Failed to fetch from backend');

      const data = await response.json();
      
      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'HDFC Bot',
        text: data.answer,
        type: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        source: data.source,
        lastUpdated: data.last_updated,
        isAdvice: data.is_advice
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (error) {
      console.error(error);
      const errorMsg = {
        id: Date.now() + 1,
        sender: 'HDFC Bot',
        text: "Sorry, I'm having trouble connecting to the server. Please ensure the backend is running.",
        type: 'assistant',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <div className="bot-info">
          <div className="bot-logo">H</div>
          <div className="bot-name">HDFC Fund Guide</div>
        </div>
        <div className="header-icons">
          <span>⟳</span>
          <span>⤢</span>
          <span>✕</span>
        </div>
      </header>

      <main className="chat-history" ref={historyRef}>
        <div className="date-divider">{new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}</div>
        
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.type}`}>
            <div className="avatar">
              {msg.type === 'assistant' ? '🤖' : '👤'}
            </div>
            <div className="message-content">
              <span className="sender-name">{msg.type === 'assistant' ? 'HDFC Bot' : 'You'}</span>
              <div className="bubble">
                {msg.text}
                <div className="msg-footer">
                  {msg.source && !msg.isAdvice && (
                   <a href={msg.source} target="_blank" rel="noopener noreferrer" className="source-link">
                      Official Source →
                    </a>
                  )}
                  <span className="timestamp">{msg.timestamp}</span>
                </div>
                {msg.lastUpdated && <div className="last-updated">Verified on: {msg.lastUpdated}</div>}
              </div>

              {msg.options && (
                <div className="options-container">
                  {msg.options.map((opt, idx) => (
                    <button 
                      key={idx} 
                      className="option-btn"
                      onClick={() => handleSend(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                  <button className="option-btn filled">Talk to an expert (External)</button>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="message-row assistant">
             <div className="avatar">🤖</div>
             <div className="typing-indicator">
               <div className="dot"></div>
               <div className="dot"></div>
               <div className="dot"></div>
             </div>
          </div>
        )}
      </main>

      <footer className="footer-area">
        <form className="input-area" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
          <input 
            type="text" 
            className="chat-input" 
            placeholder="Type a message..." 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button className="send-btn" type="submit" disabled={!input.trim() || isLoading}>
            <span style={{fontSize: '20px'}}>➤</span>
          </button>
        </form>
        <div className="footer">
          Powered by <strong>HDFC RAG-Agent</strong>
        </div>
      </footer>
    </div>
  );
}

export default App;
