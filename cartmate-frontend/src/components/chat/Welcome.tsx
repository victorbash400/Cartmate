import React from 'react';
import ChatInput from './ChatInput';
import { ShoppingBag } from 'lucide-react';
import preImage from '../../assets/pre.jpg';

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
    <div className="h-screen flex items-center justify-center p-8 bg-cover bg-center bg-no-repeat relative overflow-hidden" style={{ backgroundImage: `url(${preImage})` }}>
      {/* Overlay for better text readability */}
      <div className="absolute inset-0 bg-black/20"></div>
      
      {/* Top left logo */}
      <div className="absolute top-6 left-6 z-20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-full flex items-center justify-center">
            <ShoppingBag className="w-5 h-5 text-white" />
          </div>
          <span className="text-black text-xl font-bold">CartMate</span>
        </div>
      </div>
      
      <div className="text-center max-w-[600px] w-full z-10">

        {/* Main greeting */}
        <div className="mb-8">
          <h2 className="text-4xl font-semibold text-black mb-4">{greeting}!</h2>
        </div>

        {/* Input section */}
        <div className="w-full">
          <ChatInput
            value={input}
            onChange={onInputChange}
            onSubmit={onSubmit}
            placeholder="Tell me what you're looking for..."
            disabled={isLoading}
            isLoading={isLoading}
          />
        </div>

        {/* Quick suggestions */}
        <div className="mt-8">
          <p className="text-black/70 text-sm mb-4">Try asking:</p>
          <div className="flex flex-wrap gap-2 justify-center">
            {[
              "Find me a summer dress",
              "Show me running shoes",
              "What's trending in fashion?",
              "Help me plan an outfit"
            ].map((suggestion, index) => (
              <button
                key={index}
                onClick={() => onInputChange(suggestion)}
                className="px-4 py-2 bg-black/10 backdrop-blur-sm text-black text-sm rounded-full border border-black/20 hover:bg-black/20 transition-all duration-200"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Welcome;
