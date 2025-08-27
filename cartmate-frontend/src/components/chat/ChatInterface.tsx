import React from 'react';
import RoomScene from '../scene/RoomScene';
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
      {/* Room scene in the middle section */}
      <RoomScene />
    </div>
  );
};

export default ChatInterface;