import React from 'react';
import { Check } from 'lucide-react';

interface ConnectionStatusProps {
  sessionId: string;
  userId: string;
  message: string;
  timestamp?: Date;
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({ 
  sessionId, 
  userId, 
  message, 
  timestamp = new Date() 
}) => {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
      <Check size={12} className="text-green-500" />
      <span>Connected</span>
    </div>
  );
};

export default ConnectionStatus;
