// Product interface for e-commerce items
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