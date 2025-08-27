import React from 'react';
import ChatInput from './ChatInput';
import './Welcome.css';

interface WelcomeProps {
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isLoading: boolean;
}

const getGreeting = () => {
  // Get current time in East Africa Time (UTC+3)
  const now = new Date();
  const eatTime = new Date(now.getTime() + (3 * 60 * 60 * 1000)); // Add 3 hours for EAT
  const hours = eatTime.getUTCHours();
  
  if (hours >= 5 && hours < 12) {
    return "Good morning";
  } else if (hours >= 12 && hours < 18) {
    return "Good afternoon";
  } else {
    return "Good evening";
  }
};

const Welcome: React.FC<WelcomeProps> = ({ 
  input, 
  onInputChange, 
  onSubmit, 
  isLoading 
}) => {
  const greeting = getGreeting();
  
  return (
    <div className="welcome-container">
      <div className="welcome-content">
        <h1 className="welcome-title">{greeting}! What's first on your list?</h1>
        <div className="welcome-input-wrapper">
          <ChatInput
            value={input}
            onChange={onInputChange}
            onSubmit={onSubmit}
            placeholder="How can I help you today?"
            disabled={isLoading}
            isLoading={isLoading}
          />
        </div>
      </div>
    </div>
  );
};

export default Welcome;
