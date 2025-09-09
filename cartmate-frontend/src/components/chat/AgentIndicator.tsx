import React from 'react';
import { Bot, CheckCircle, Clock, AlertCircle } from 'lucide-react';

export interface AgentIndicatorProps {
  type: 'calling' | 'processing' | 'success' | 'error';
  agentName: string;
  message: string;
  step?: number;
  totalSteps?: number;
}

const AgentIndicator: React.FC<AgentIndicatorProps> = ({ 
  type, 
  agentName, 
  message, 
  step, 
  totalSteps 
}) => {
  const getIcon = () => {
    switch (type) {
      case 'calling':
        return <Bot size={12} className="text-orange-500" />;
      case 'processing':
        return <Clock size={12} className="text-blue-500 animate-spin" />;
      case 'success':
        return <CheckCircle size={12} className="text-green-500" />;
      case 'error':
        return <AlertCircle size={12} className="text-red-500" />;
      default:
        return <Bot size={12} className="text-gray-500" />;
    }
  };

  const getBackgroundColor = () => {
    switch (type) {
      case 'calling':
        return 'bg-orange-50 border-orange-200';
      case 'processing':
        return 'bg-blue-50 border-blue-200';
      case 'success':
        return 'bg-green-50 border-green-200';
      case 'error':
        return 'bg-red-50 border-red-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getTextColor = () => {
    switch (type) {
      case 'calling':
        return 'text-orange-700';
      case 'processing':
        return 'text-blue-700';
      case 'success':
        return 'text-green-700';
      case 'error':
        return 'text-red-700';
      default:
        return 'text-gray-700';
    }
  };

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${getBackgroundColor()} ${getTextColor()} shadow-sm`}>
      {getIcon()}
      <span className="font-semibold">{agentName}</span>
      <span className="text-gray-500">•</span>
      <span>{message}</span>
      {step && totalSteps && (
        <>
          <span className="text-gray-400">•</span>
          <span className="text-gray-500 text-xs">{step}/{totalSteps}</span>
        </>
      )}
    </div>
  );
};

export default AgentIndicator;
