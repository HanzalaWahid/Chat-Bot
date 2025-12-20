import React, { useState, useRef, useEffect } from 'react';
import { Utensils, X, ChevronLeft, Loader2, Zap, Menu, Clock, MapPin, Truck } from 'lucide-react';
import './App.css';


const BOT_NAME = "AI Assistant";

const initialMessages = [
  { sender: 'bot', text: 'Hi there! 👋 Welcome!\n\nI can help you with:\n• View our menu\n• Check opening hours\n• Find our branches\n• Answer FAQs\n\nHow can I help you today?' },
];

const quickActions = [
  { label: "View Menu", action: "Show me the menu", icon: Menu, flag: 'shown_menu' },
  { label: "Opening Hours", action: "What are your hours", icon: Clock, flag: 'shown_hours' },
  { label: "Our Branches", action: "Where are your branches", icon: MapPin, flag: 'shown_branches' },
  { label: "Delivery Info", action: "Do you offer delivery", icon: Truck, flag: 'shown_delivery' },
];

const ChatMessage = ({ message }) => {
  const isBot = message.sender === 'bot';
  const avatarClass = isBot ? "avatar-bot" : "avatar-user";
  const bubbleClass = isBot ? "chat-bubble-bot" : "chat-bubble-user";

  // Format text to preserve newlines and add basic formatting
  const formatText = (text) => {
    const lines = text.split('\n');
    return lines.map((line, index) => {
      const isHeader = line.startsWith('📋') || line.startsWith('📊') || line.startsWith('📍') || line.startsWith('🕐');
      const isSeparator = line.includes('━━');
      const isListItem = /^\d+\./.test(line.trim()) || line.trim().startsWith('•');
      const isBold = line.includes('**');
      let formattedLine = line;
      if (isBold) {
        formattedLine = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      }
      const key = `${index}-${line.substring(0, 20)}`;
      if (isSeparator) {
        return <div key={key} style={{ borderTop: '1px solid rgba(255,255,255,0.1)', margin: '4px 0' }}></div>;
      }
      if (isHeader) {
        return <div key={key} style={{ fontWeight: 'bold', marginTop: index > 0 ? '8px' : '0', marginBottom: '4px', fontSize: '15px' }}>{formattedLine.replace(/\*\*/g, '')}</div>;
      }
      if (isListItem) {
        return <div key={key} style={{ marginLeft: '8px', marginBottom: '2px' }} dangerouslySetInnerHTML={{ __html: formattedLine }}></div>;
      }
      if (line.trim() === '') {
        return <div key={key} style={{ height: '4px' }}></div>;
      }
      return <div key={key} style={{ marginBottom: '2px' }} dangerouslySetInnerHTML={{ __html: formattedLine }}></div>;
    });
  };

  return (
    <div className={`chat-message ${isBot ? 'bot' : 'user'}`}>
      {isBot && <div className={avatarClass}><Utensils size={16} /></div>}
      <div className={bubbleClass} style={{ whiteSpace: 'pre-wrap', wordWrap: 'break-word' }}>
        {formatText(message.text)}
      </div>
      {!isBot && <div className={avatarClass}>👤</div>}
    </div>
  );
};


const App = () => {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionFlags, setSessionFlags] = useState({});
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(scrollToBottom, [messages]);
  useEffect(() => { inputRef.current?.focus(); }, []);

  // Helper to extract session flags from bot response (if present)
  function extractSessionFlagsFromHeaders(headers) {
    // Not implemented: If backend returns flags in headers, parse here
    // For now, we update flags based on the action sent
    return null;
  }

  // Map quick action to session flag
  function getFlagForAction(action) {
    const found = quickActions.find(q => q.action === action);
    return found ? found.flag : null;
  }

  const handleSendMessage = async (text) => {
    if (!text.trim()) return;
    setMessages(prev => [...prev, { sender: 'user', text }]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      setMessages(prev => [...prev, { sender: 'bot', text: data.response || 'No response from server' }]);

      // Use sessionFlags from backend to hide quick actions after use
      if (data.sessionFlags) {
        setSessionFlags(data.sessionFlags);
      } else {
        // Fallback: Hide quick action if it was a one-time action
        const flag = getFlagForAction(text);
        if (flag) {
          setSessionFlags(prev => ({ ...prev, [flag]: true }));
        }
      }
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages(prev => [...prev, { sender: 'bot', text: 'Sorry, I encountered an error. Please make sure the backend server is running.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => { e.preventDefault(); handleSendMessage(input); };
  const handleQuickAction = (action) => handleSendMessage(action);

  return (
    <div className="chat-container">
      <div className="chat-header">
        <div className="chat-header-left">
          <ChevronLeft size={20} />
          <strong>{BOT_NAME}</strong>
        </div>
        <X size={20} className="chat-close-icon" />
      </div>

      <div className="chat-messages">
        {messages.map((m, i) => <ChatMessage key={i} message={m} />)}

        {isLoading && (
          <div className="chat-message bot">
            <div className="avatar-bot"><Utensils size={18} /></div>
            <div className="loader-msg"><Loader2 size={16} />ChefBot is thinking...</div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="divider"></div>

      <div className="quick-actions-container">
        {quickActions.filter(item => !sessionFlags[item.flag]).map((item, idx) => (
          <button key={idx} className="quick-action-btn" onClick={() => handleQuickAction(item.action)} disabled={isLoading}>
            <item.icon size={16} style={{ marginRight: '8px' }} />
            {item.label}
          </button>
        ))}
      </div>

      <form className="chat-input-area" onSubmit={handleSubmit}>
        <div className="input-container">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message…"
            className="input-field"
            disabled={isLoading}
          />
        </div>
        <button
          type="submit"
          className={`btn-submit ${input.trim() ? 'btn-submit-enabled' : 'btn-submit-disabled'}`}
          disabled={isLoading || !input.trim()}
          aria-label="Send message"
        >
          <span style={{ fontSize: '1.3em' }}>➤</span>
        </button>
      </form>
    </div>
  );
};


export default App;
