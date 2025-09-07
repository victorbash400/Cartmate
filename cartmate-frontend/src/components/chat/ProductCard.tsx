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
    <div className="bg-white border border-gray-200 rounded-lg shadow-md p-4 max-w-xs">
      <img src={`/images/products/${product.picture}`} alt={product.name} className="w-full h-48 object-cover rounded-t-lg" />
      <div className="pt-4">
        <h3 className="text-lg font-semibold text-gray-800">{product.name}</h3>
        <p className="text-gray-600 mt-1">{formatPrice(product.priceUsd)}</p>
      </div>
    </div>
  );
};

export default ProductCard;
