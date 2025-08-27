import React, { useEffect, useState } from 'react';
import './AgentGroupChat.css';

interface AgentGroupChatProps {
  isVisible: boolean;
  toggleVisibility: () => void;
}

const AgentGroupChat: React.FC<AgentGroupChatProps> = ({ isVisible, toggleVisibility }) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth <= 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const handleOverlayClick = () => {
    if (isMobile) {
      toggleVisibility();
    }
  };

  return (
    <>
      {/* Mobile overlay */}
      {isMobile && (
        <div 
          className={`agent-group-overlay ${isVisible ? 'active' : ''}`}
          onClick={handleOverlayClick}
        />
      )}
      
      <div className={`agent-group-chat ${isVisible ? 'visible' : ''}`} />
    </>
  );
};

export default AgentGroupChat;