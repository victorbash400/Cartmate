import React from 'react';

export interface Product {
  id: string;
  name: string;
  picture: string;
  priceUsd: {
    currencyCode: string;
    units: number;
    nanos: number;
  };
}

interface ProductCardProps {
  product: Product;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const formatPrice = (price: Product['priceUsd']) => {
    const dollars = price.units;
    const cents = Math.round(price.nanos / 10000000);
    return `$${dollars}.${cents.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md p-3 max-w-xs transition-all duration-300 hover:shadow-lg hover:scale-105 hover:border-orange-300">
      <img 
        src={`/images/products/${product.picture}`} 
        alt={product.name} 
        className="w-full h-40 object-cover rounded-t-lg transition-transform duration-300 hover:scale-105" 
      />
      <div className="pt-3">
        <h3 className="text-sm font-semibold text-gray-800 leading-tight">{product.name}</h3>
        <p className="text-orange-600 font-bold mt-1 text-sm">{formatPrice(product.priceUsd)}</p>
      </div>
    </div>
  );
};

export default ProductCard;
