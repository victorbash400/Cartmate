import React from 'react';
import './ChatInterface.css';

interface ChatInterfaceProps {
  onChatStartedChange: (started: boolean) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ onChatStartedChange }) => {
  // Notify parent that chat is not started (empty state)
  React.useEffect(() => {
    onChatStartedChange(false);
  }, [onChatStartedChange]);

  return (
    <div className="chat-interface">
      {/* Empty middle section - all chat functionality moved to AgentGroupChat */}
    </div>
  );
};

export default ChatInterface;