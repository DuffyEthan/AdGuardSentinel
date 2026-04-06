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
  isLoading?: boolean;
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
  isLoading = false,
}: SentinelAssistantProps) {
  const [input, setInput] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change or loading state changes
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  function handleSend() {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
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
      {/* Header */}
      <div className="sentinel-assistant__header">
        <span className="sentinel-assistant__dot" />
        <h3 className="panel-title sentinel-assistant__title">Sentinel Assistant</h3>
      </div>

      {/* Publisher selector */}
      <select
        className="sentinel-assistant__select"
        value={selectedPublisher}
        onChange={e => onPublisherChange(e.target.value)}
      >
        {publishers.map(p => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Preset action buttons */}
      <div className="sentinel-assistant__actions">
        <button
          className="sentinel-action-btn"
          onClick={onExplainTrust}
          disabled={isLoading}
        >
          Explain trust score for <em>{selectedPublisher}</em>
          <span className="sentinel-action-chevron">&#8250;</span>
        </button>
        <button
          className="sentinel-action-btn"
          onClick={onShowAnomalies}
          disabled={isLoading}
        >
          Show anomalies &amp; evidence
          <span className="sentinel-action-chevron">&#8250;</span>
        </button>
        <button
          className="sentinel-action-btn"
          onClick={onCompareNetwork}
          disabled={isLoading}
        >
          Compare against network
          <span className="sentinel-action-chevron">&#8250;</span>
        </button>
      </div>

      {/* Messages area */}
      <div className="sentinel-assistant__messages" ref={scrollRef}>
        {messages.map((msg, i) => (
          <div
            key={i}
            className={
              `sentinel-message sentinel-message--${msg.role}` +
              (msg.isWarning ? ' sentinel-message--warning' : '')
            }
          >
            {msg.isWarning && <span className="sentinel-message__warn-icon">&#9888;</span>}
            <p className="sentinel-message__text">{msg.content}</p>
            {msg.bullets && msg.bullets.length > 0 && (
              <ul className="sentinel-message__bullets">
                {msg.bullets.map((b, j) => <li key={j}>{b}</li>)}
              </ul>
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="sentinel-message sentinel-message--assistant sentinel-typing">
            <div className="sentinel-typing__dots">
              <span />
              <span />
              <span />
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="sentinel-assistant__input">
        <input
          className="sentinel-input"
          type="text"
          placeholder="Ask a question..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
        />
        <button
          className="btn btn--inline sentinel-send-btn"
          onClick={handleSend}
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default SentinelAssistant;
