import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../../types/sentinel';

interface SentinelAssistantProps {
  publishers: string[];
  selectedPublisher: string;
  onPublisherChange: (name: string) => void;
  onExplainTrust: () => void;
  onShowAnomalies: () => void;
  onCompareNetwork: () => void;
  messages: ChatMessage[];
  onSendMessage: (text: string) => void;
}

function SentinelAssistant({
  publishers,
  selectedPublisher,
  onPublisherChange,
  onExplainTrust,
  onShowAnomalies,
  onCompareNetwork,
  messages,
  onSendMessage,
}: SentinelAssistantProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInput('');
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="panel sentinel-assistant">
      <div className="sentinel-assistant__header">
        <span className="sentinel-assistant__dot" />
        <h3 className="panel-title sentinel-assistant__title">Sentinel Assistant</h3>
      </div>

      <select
        className="sentinel-assistant__select"
        value={selectedPublisher}
        onChange={e => onPublisherChange(e.target.value)}
      >
        {publishers.map(p => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      <div className="sentinel-assistant__actions">
        <button className="sentinel-action-btn" onClick={onExplainTrust}>
          Explain trust score for <em>{selectedPublisher}</em>
          <span className="sentinel-action-chevron">›</span>
        </button>
        <button className="sentinel-action-btn" onClick={onShowAnomalies}>
          Show anomalies &amp; evidence
          <span className="sentinel-action-chevron">›</span>
        </button>
        <button className="sentinel-action-btn" onClick={onCompareNetwork}>
          Compare against network
          <span className="sentinel-action-chevron">›</span>
        </button>
      </div>

      <div className="sentinel-assistant__messages" ref={messagesEndRef}>
        {messages.map((msg, i) => (
          <div key={i} className={`sentinel-message sentinel-message--${msg.role}${msg.isWarning ? ' sentinel-message--warning' : ''}`}>
            {msg.isWarning && <span className="sentinel-message__warn-icon">⚠</span>}
            <p className="sentinel-message__text">{msg.content}</p>
            {msg.bullets && msg.bullets.length > 0 && (
              <ul className="sentinel-message__bullets">
                {msg.bullets.map((b, j) => <li key={j}>{b}</li>)}
              </ul>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="sentinel-assistant__input">
        <input
          className="sentinel-input"
          type="text"
          placeholder="Ask a question..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="btn btn--inline sentinel-send-btn" onClick={handleSend}>
          Send
        </button>
      </div>
    </div>
  );
}

export default SentinelAssistant;
