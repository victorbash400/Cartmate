import React, { useState, useEffect } from 'react';
import { ExternalLink } from 'lucide-react';

interface Ad {
  redirect_url: string;
  text: string;
}

interface InlineAdsProps {
  ads: Ad[];
  context?: string[];
  isLoading?: boolean;
}

export const InlineAds: React.FC<InlineAdsProps> = ({ ads, context, isLoading }) => {
  const [currentAdIndex, setCurrentAdIndex] = useState(0);

  // Limit ads to maximum of 4
  const limitedAds = ads.slice(0, 4);

  // Rotate through ads every 5 seconds
  useEffect(() => {
    if (limitedAds.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentAdIndex((prev) => (prev + 1) % limitedAds.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [limitedAds.length]);

  const handleAdClick = (ad: Ad) => {
    // In a real app, you'd track the click and redirect
    console.log('Ad clicked:', ad);
    // For now, just log it
    alert(`Ad clicked: ${ad.text}\nWould redirect to: ${ad.redirect_url}`);
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-black rounded-full flex items-center justify-center">
            <span className="text-white text-xs font-bold">Ad</span>
          </div>
          <h3 className="text-sm font-medium text-gray-600">Sponsored</h3>
        </div>
        
        <div className="space-y-2">
          {[1, 2].map((i) => (
            <div key={i} className="bg-gray-50 rounded-lg p-3 animate-pulse">
              <div className="h-3 bg-gray-200 rounded mb-2"></div>
              <div className="h-2 bg-gray-200 rounded w-2/3"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!limitedAds || limitedAds.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5 bg-black rounded-full flex items-center justify-center">
            <span className="text-white text-xs font-bold">Ad</span>
          </div>
          <h3 className="text-sm font-medium text-gray-600">Sponsored</h3>
        </div>
        
        <div className="text-center text-gray-500 text-sm py-4">
          No ads available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-5 h-5 bg-black rounded-full flex items-center justify-center">
          <span className="text-white text-xs font-bold">Ad</span>
        </div>
        <h3 className="text-sm font-medium text-gray-900">Sponsored</h3>
        {context && context.length > 0 && (
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            {context[0]}
          </span>
        )}
      </div>
      
      <div className="space-y-2">
        {limitedAds.map((ad, index) => (
          <div
            key={index}
            className={`bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg p-3 border border-gray-200 cursor-pointer transition-all duration-200 hover:shadow-md hover:border-gray-300 ${
              index === currentAdIndex ? 'ring-2 ring-gray-300' : ''
            }`}
            onClick={() => handleAdClick(ad)}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <p className="text-xs text-gray-800 leading-relaxed">
                  {ad.text}
                </p>
              </div>
              <ExternalLink className="w-3 h-3 text-gray-600 ml-2 flex-shrink-0" />
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-700 font-medium">
                Learn More
              </span>
              {limitedAds.length > 1 && (
                <div className="flex space-x-1">
                  {limitedAds.map((_, dotIndex) => (
                    <div
                      key={dotIndex}
                      className={`w-1.5 h-1.5 rounded-full ${
                        dotIndex === currentAdIndex ? 'bg-gray-600' : 'bg-gray-300'
                      }`}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      <div className="mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-500 text-center">
          Ads help keep CartMate free
        </p>
      </div>
    </div>
  );
};
