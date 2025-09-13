import React from 'react';
import ReactMarkdown from 'react-markdown';
import { ExternalLink, DollarSign, TrendingUp, CheckCircle, AlertCircle } from 'lucide-react';

interface PriceComparisonData {
  original_product: {
    name: string;
    priceUsd: {
      units: number;
      nanos: number;
    };
    description?: string;
  };
  current_price: string;
  price_analysis: string;
  similar_products: Array<{
    name: string;
    price: string;
    description: string;
    source: string;
    url: string;
    retailer: string;
  }>;
  sources: Array<{
    title: string;
    url: string;
    snippet: string;
    date: string;
    last_updated: string;
  }>;
  citations: string[];
  raw_content: string;
  api_usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    search_context_size: string;
    cost: {
      input_tokens_cost: number;
      output_tokens_cost: number;
      request_cost: number;
      total_cost: number;
    };
  };
  total_cost: number;
}

interface PriceComparisonProps {
  priceComparison: PriceComparisonData | any; // Make it more flexible for debugging
}

const PriceComparison: React.FC<PriceComparisonProps> = ({ priceComparison }) => {
  // Debug: Log the received data
  console.log('PriceComparison - Received data:', priceComparison);
  
  // Check if priceComparison data exists
  if (!priceComparison) {
    return (
      <div className="w-full bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
        <div className="text-center text-gray-500">
          <p>Price comparison data is not available.</p>
        </div>
      </div>
    );
  }

  // Safely extract data with fallbacks
  const original_product = priceComparison?.original_product || {};
  const current_price = priceComparison?.current_price || "Unknown";
  const price_analysis = priceComparison?.price_analysis || "";
  const similar_products = priceComparison?.similar_products || [];
  const sources = priceComparison?.sources || [];
  // const citations = priceComparison?.citations || [];
  
  // Safely get product name
  const productName = original_product?.name || "Unknown Product";

  // If we have an error in the data, show it
  if (priceComparison?.error) {
    return (
      <div className="w-full bg-white border border-red-200 rounded-lg p-6 shadow-sm">
        <div className="text-center text-red-600">
          <h3 className="text-lg font-semibold mb-2">Price Comparison Error</h3>
          <p>{priceComparison.error}</p>
        </div>
      </div>
    );
  }

  // If we don't have the expected data structure, show a fallback
  if (!original_product || Object.keys(original_product).length === 0) {
    return (
      <div className="w-full bg-white border border-yellow-200 rounded-lg p-6 shadow-sm">
        <div className="text-center text-yellow-600">
          <h3 className="text-lg font-semibold mb-2">Price Comparison Data</h3>
          <p>Received price comparison data, but structure is unexpected.</p>
          <details className="mt-4 text-left">
            <summary className="cursor-pointer text-sm">Show raw data</summary>
            <pre className="mt-2 text-xs bg-gray-100 p-2 rounded overflow-auto">
              {JSON.stringify(priceComparison, null, 2)}
            </pre>
          </details>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      {/* Header - Compact */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-green-100 rounded-lg">
            <DollarSign className="w-4 h-4 text-green-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Price Check</h3>
            <p className="text-xs text-gray-500">{productName}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900">{current_price}</p>
        </div>
      </div>

      {/* Quick Analysis - Compact with Verdict */}
      {price_analysis && (
        <div className="mb-3 p-3 bg-gray-50 rounded-lg">
          <div className="flex items-start gap-2">
            {price_analysis.includes('✅') ? (
              <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
            ) : price_analysis.includes('❌') ? (
              <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
            ) : (
              <TrendingUp className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
            )}
            <div className="text-xs text-gray-700 leading-relaxed">
              <ReactMarkdown
                components={{
                  p: ({ children }) => <p className="mb-1">{children}</p>,
                  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  em: ({ children }) => <em className="italic">{children}</em>,
                  ul: ({ children }) => <ul className="list-disc pl-3 mb-1">{children}</ul>,
                  li: ({ children }) => <li className="mb-0.5">{children}</li>,
                }}
              >
                {price_analysis}
              </ReactMarkdown>
            </div>
          </div>
        </div>
      )}

      {/* Similar Products - Compact Grid */}
      {similar_products && similar_products.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Similar Products</h4>
          <div className="grid grid-cols-1 gap-2">
            {similar_products.slice(0, 3).map((product: any, index: number) => (
              <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-900 truncate">{product.name}</p>
                  <p className="text-xs text-gray-500">{product.retailer}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-gray-900">{product.price}</span>
                  {product.url && (
                    <a
                      href={product.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1 text-blue-600 hover:text-blue-800"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sources - Compact Pills */}
      {sources && sources.length > 0 && (
        <div className="mb-3">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Sources</h4>
          <div className="flex flex-wrap gap-1.5">
            {sources.slice(0, 6).map((source: any, index: number) => (
              <a
                key={index}
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs hover:bg-blue-100 transition-colors"
              >
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                {source.title.length > 20 ? source.title.substring(0, 20) + '...' : source.title}
              </a>
            ))}
            {sources.length > 6 && (
              <span className="inline-flex items-center px-2 py-1 bg-gray-100 text-gray-600 rounded-full text-xs">
                +{sources.length - 6} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Footer - Minimal */}
      <div className="pt-2 border-t border-gray-100">
        <p className="text-xs text-gray-400 text-center">
          Market data • Prices may vary
        </p>
      </div>
    </div>
  );
};

export default PriceComparison;
