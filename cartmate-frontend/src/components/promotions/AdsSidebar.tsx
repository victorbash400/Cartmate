import React, { useState, useEffect } from 'react';
import { ExternalLink, Sparkles } from 'lucide-react';

interface Ad {
  redirect_url: string;
  text: string;
}

interface AdsSidebarProps {
  ads: Ad[];
  context?: string[];
  isLoading?: boolean;
}

export const AdsSidebar: React.FC<AdsSidebarProps> = ({ ads, context, isLoading }) => {
  const [currentAdIndex, setCurrentAdIndex] = useState(0);

  // Rotate through ads every 5 seconds
  useEffect(() => {
    if (ads.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentAdIndex((prev) => (prev + 1) % ads.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [ads.length]);

  const handleAdClick = (ad: Ad) => {
    // In a real app, you'd track the click and redirect
    console.log('Ad clicked:', ad);
    // For now, just log it
    alert(`Ad clicked: ${ad.text}\nWould redirect to: ${ad.redirect_url}`);
  };

  if (isLoading) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-600">Sponsored</h3>
        </div>
        
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded mb-2"></div>
              <div className="h-3 bg-gray-200 rounded w-3/4"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!ads || ads.length === 0) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-4">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-gray-400" />
          </div>
          <h3 className="text-sm font-medium text-gray-600">Sponsored</h3>
        </div>
        
        <div className="text-center text-gray-500 text-sm py-8">
          No ads available
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-white border-l border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center">
          <Sparkles className="w-3 h-3 text-blue-600" />
        </div>
        <h3 className="text-sm font-medium text-gray-900">Sponsored</h3>
        {context && context.length > 0 && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {context[0]}
          </span>
        )}
      </div>
      
      <div className="space-y-3">
        {ads.map((ad, index) => (
          <div
            key={index}
            className={`bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-100 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-blue-200 ${
              index === currentAdIndex ? 'ring-2 ring-blue-200' : ''
            }`}
            onClick={() => handleAdClick(ad)}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="text-sm text-gray-800 leading-relaxed">
                  {ad.text}
                </p>
              </div>
              <ExternalLink className="w-3 h-3 text-blue-500 ml-2 flex-shrink-0" />
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-xs text-blue-600 font-medium">
                Learn More
              </span>
              {ads.length > 1 && (
                <div className="flex space-x-1">
                  {ads.map((_, dotIndex) => (
                    <div
                      key={dotIndex}
                      className={`w-1.5 h-1.5 rounded-full ${
                        dotIndex === currentAdIndex ? 'bg-blue-500' : 'bg-blue-200'
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-4 border-t border-gray-100">
        <p className="text-xs text-gray-500 text-center">
          Ads help keep CartMate free
        </p>
      </div>
    </div>
  );
};
