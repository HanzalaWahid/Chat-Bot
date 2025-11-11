// frontend/src/components/ChatBot.jsx
import React, { useState } from 'react';

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    // Example initial bot message with quick-action buttons
    { from: 'bot', text: 'Welcome! How can I help you today?', actions: ['View menu', 'Book a table'] }
  ]);
  const [input, setInput] = useState('');

  // Toggle chat window open/close
  const handleToggle = () => {
    setOpen(prev => !prev);
  };

  // Send a message to backend and append bot response
  const sendMessage = async (text) => {
    // Append user message
    setMessages(prev => [...prev, { from: 'user', text }]);

    try {
      // POST to FastAPI backend via proxy
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      
      const data = await res.json();
      // Backend returns { response: "..." }
      setMessages(prev => [...prev, { 
        from: 'bot', 
        text: data.response || 'No response', 
        actions: [] 
      }]);
    } catch (err) {
      console.error('Error sending message:', err);
      setMessages(prev => [...prev, { 
        from: 'bot', 
        text: 'Sorry, I encountered an error. Please make sure the backend server is running.',
        actions: []
      }]);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;
    setInput('');      // clear input box
    sendMessage(trimmed);
  };

  // Handle quick-action button click
  const handleQuick = (action) => {
    sendMessage(action);
  };

  return (
    <div className="fixed bottom-4 right-4 z-50">
      {/* Chat icon (bubble) */}
      {!open && (
        <button onClick={handleToggle}
                className="bg-blue-600 text-white rounded-full p-4 shadow-lg">
          💬
        </button>
      )}
      {/* Expanded chat panel */}
      {open && (
        <div className="flex flex-col h-96 w-80 bg-white shadow-lg rounded-lg overflow-hidden">
          {/* Header with emoji avatar */}
          <div className="flex items-center p-4 bg-teal-600 text-white">
            <span role="img" aria-label="restaurant" className="text-2xl">🍽️</span>
            <span className="ml-2 font-semibold">Restaurant</span>
            <button onClick={handleToggle} className="ml-auto text-2xl">&times;</button>
          </div>
          {/* Message list (scrollable) */}
          <div className="flex-1 px-4 py-2 overflow-y-auto space-y-2">
            {messages.map((msg, idx) => (
              <div key={idx}
                   className={`flex ${msg.from==='bot' ? 'justify-start' : 'justify-end'}`}>
                <div className={`max-w-xs px-3 py-2 rounded-lg 
                                 ${msg.from==='bot' ? 'bg-gray-100 text-gray-900' : 'bg-blue-500 text-white'}`}>
                  {msg.text}
                  {/* Quick-action buttons after bot messages */}
                  {msg.from==='bot' && msg.actions && msg.actions.length > 0 && (
                    <div className="flex space-x-2 mt-2">
                      {msg.actions.map(action => (
                        <button key={action}
                                onClick={() => handleQuick(action)}
                                className="px-2 py-1 bg-blue-100 text-blue-800 rounded">
                          {action}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          {/* Input field */}
          <form onSubmit={handleSubmit} className="flex p-2 border-t border-gray-300">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Type a message..."
              className="flex-grow px-3 py-2 border border-gray-300 rounded-full 
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button type="submit"
                    className="ml-2 bg-blue-600 text-white p-2 rounded-full">
              ➤
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
