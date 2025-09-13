import React from 'react';
import type { Product } from './types';

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const formatPrice = (price: Product['priceUsd']) => {
    const dollars = price.units;
    const cents = Math.round(price.nanos / 100000000);
    return `$${dollars}.${cents.toString().padStart(2, '0')}`;
  };

  const getImageSrc = () => {
    console.log('ProductCard - Product data:', product);
    console.log('ProductCard - Picture URL:', product.picture);
    
    if (!product.picture) {
      console.log('ProductCard - No picture, using placeholder');
      return '/images/products/placeholder.svg';
    }
    
    // Handle different image URL formats
    if (product.picture.startsWith('http')) {
      console.log('ProductCard - Using full HTTP URL:', product.picture);
      return product.picture; // Full URL
    } else if (product.picture.startsWith('/static/')) {
      // Online Boutique static images - use the deployed frontend service
      // The frontend service is exposed as LoadBalancer with external IP
      const frontendUrl = `http://34.10.248.251${product.picture}`;
      console.log('ProductCard - Using Online Boutique frontend service:', frontendUrl);
      return frontendUrl;
    } else if (product.picture.startsWith('/')) {
      console.log('ProductCard - Using absolute path:', product.picture);
      return product.picture; // Absolute path
    } else {
      const relativePath = `/images/products/${product.picture}`;
      console.log('ProductCard - Using relative path:', relativePath);
      return relativePath; // Relative path
    }
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    // Fallback to placeholder if image fails to load
    console.log('ProductCard - Image failed to load:', e.currentTarget.src);
    console.log('ProductCard - Falling back to placeholder');
    e.currentTarget.src = '/images/products/placeholder.svg';
  };

  return (
    <div className="bg-white border border-gray-100 rounded-lg overflow-hidden hover:border-gray-200 transition-colors duration-200 aspect-square relative">
      <img 
        src={getImageSrc()} 
        alt={product.name} 
        className="w-full h-full object-cover" 
        onError={handleImageError}
      />
      <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 p-1.5">
        <h3 className="text-xs font-medium text-white mb-0.5 line-clamp-1">{product.name}</h3>
        <p className="text-orange-300 font-semibold text-xs">{formatPrice(product.priceUsd)}</p>
      </div>
    </div>
  );
};

export default ProductCard;