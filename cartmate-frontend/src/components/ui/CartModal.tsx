import React, { useState, useEffect } from 'react';
import { X, ShoppingBag, Trash2, Plus, Minus, DollarSign } from 'lucide-react';

interface CartModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId?: string;
}

interface CartItem {
  product_id: string;
  name: string;
  price: string;
  quantity: number;
  image_url?: string;
  picture?: string;
}

interface CartData {
  items: CartItem[];
  total_items: number;
  total_price?: number;
}

const CartModal: React.FC<CartModalProps> = ({ isOpen, onClose, sessionId }) => {
  const [cartData, setCartData] = useState<CartData>({ items: [], total_items: 0 });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pendingChanges, setPendingChanges] = useState<{
    updates: { [productId: string]: number };
    removes: string[];
  }>({ updates: {}, removes: [] });
  const [hasChanges, setHasChanges] = useState(false);

  const getImageSrc = (item: CartItem) => {
    const imageUrl = item.image_url || item.picture;
    
    if (!imageUrl) {
      return '/images/products/placeholder.svg';
    }
    
    // Handle different image URL formats (same logic as ProductCard)
    if (imageUrl.startsWith('http')) {
      return imageUrl; // Full URL
    } else if (imageUrl.startsWith('/static/')) {
      // Online Boutique static images - use the deployed frontend service
      const frontendUrl = `http://34.10.248.251${imageUrl}`;
      return frontendUrl;
    } else if (imageUrl.startsWith('/')) {
      return imageUrl; // Absolute path
    } else {
      const relativePath = `/images/products/${imageUrl}`;
      return relativePath; // Relative path
    }
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement, Event>) => {
    // Fallback to placeholder if image fails to load
    e.currentTarget.src = '/images/products/placeholder.svg';
  };

  useEffect(() => {
    if (isOpen && sessionId) {
      loadCart();
      // Reset pending changes when modal opens
      setPendingChanges({ updates: {}, removes: [] });
      setHasChanges(false);
    }
  }, [isOpen, sessionId]);

  const loadCart = async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const apiUrl = window.location.hostname === '35.222.124.181' ? 'http://34.42.109.18:8000' : 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/cart/${sessionId}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      if (result.success) {
        setCartData(result.cart_data || { items: [], total_items: 0 });
      } else {
        setError(result.message || 'Failed to load cart');
      }
    } catch (error) {
      console.error('Error loading cart:', error);
      setError('Failed to load cart. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const updateQuantity = (productId: string, newQuantity: number) => {
    if (newQuantity < 0) return;
    
    setPendingChanges(prev => {
      const newChanges = { ...prev };
      
      if (newQuantity === 0) {
        // Mark for removal
        newChanges.removes.push(productId);
        // Remove from updates if it was there
        delete newChanges.updates[productId];
      } else {
        // Mark for update
        newChanges.updates[productId] = newQuantity;
        // Remove from removes if it was there
        newChanges.removes = newChanges.removes.filter(id => id !== productId);
      }
      
      return newChanges;
    });
    
    setHasChanges(true);
    
    // Update local display immediately for better UX
    if (newQuantity === 0) {
      setCartData(prev => ({
        ...prev,
        items: prev.items.filter(item => item.product_id !== productId),
        total_items: prev.total_items - 1
      }));
    } else {
      setCartData(prev => ({
        ...prev,
        items: prev.items.map(item => 
          item.product_id === productId 
            ? { ...item, quantity: newQuantity }
            : item
        )
      }));
    }
  };

  const confirmChanges = async () => {
    if (!sessionId || !hasChanges) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const apiUrl = window.location.hostname === '35.222.124.181' ? 'http://34.42.109.18:8000' : 'http://localhost:8000';
      // Apply all pending changes
      const promises = [];
      
      // Handle removals
      for (const productId of pendingChanges.removes) {
        promises.push(
          fetch(`${apiUrl}/api/cart/${sessionId}/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId })
          })
        );
      }
      
      // Handle updates
      for (const [productId, quantity] of Object.entries(pendingChanges.updates)) {
        promises.push(
          fetch(`${apiUrl}/api/cart/${sessionId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, quantity })
          })
        );
      }
      
      // Wait for all operations to complete
      const responses = await Promise.all(promises);
      const failed = responses.some(r => !r.ok);
      
      if (failed) {
        throw new Error('Some operations failed');
      }
      
      // Clear pending changes
      setPendingChanges({ updates: {}, removes: [] });
      setHasChanges(false);
      
      // Reload cart to get the actual state
      await loadCart();
      
    } catch (error) {
      console.error('Error confirming changes:', error);
      setError('Failed to save changes. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const cancelChanges = () => {
    setPendingChanges({ updates: {}, removes: [] });
    setHasChanges(false);
    // Reload cart to revert to original state
    loadCart();
  };

  const clearCart = async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    try {
      const apiUrl = window.location.hostname === '35.222.124.181' ? 'http://34.42.109.18:8000' : 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/cart/${sessionId}/clear`, {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const result = await response.json();
      if (result.success) {
        setCartData({ items: [], total_items: 0 });
        setPendingChanges({ updates: {}, removes: [] });
        setHasChanges(false);
      } else {
        setError(result.message || 'Failed to clear cart');
      }
    } catch (error) {
      console.error('Error clearing cart:', error);
      setError('Failed to clear cart. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md mx-auto transform transition-all duration-300 scale-100 pointer-events-auto border border-gray-200 h-[600px] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-orange-100 rounded-full flex items-center justify-center">
              <ShoppingBag className="w-4 h-4 text-orange-600" />
            </div>
            <h2 className="text-lg font-medium text-gray-900">Shopping Cart</h2>
            {cartData.total_items > 0 && (
              <span className="bg-orange-100 text-orange-600 text-xs px-2 py-1 rounded-full">
                {cartData.total_items} item{cartData.total_items !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <button
            onClick={handleClose}
            className="w-6 h-6 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
          >
            <X className="w-3 h-3 text-gray-600" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="w-6 h-6 border-2 border-orange-600 border-t-transparent rounded-full animate-spin" />
              <span className="ml-2 text-gray-600">Loading cart...</span>
            </div>
          ) : error ? (
            <div className="text-center h-full flex flex-col items-center justify-center p-4">
              <div className="text-red-600 mb-2">{error}</div>
              <button
                onClick={loadCart}
                className="text-orange-600 hover:text-orange-700 text-sm font-medium"
              >
                Try again
              </button>
            </div>
          ) : cartData.items.length === 0 ? (
            <div className="text-center h-full flex flex-col items-center justify-center p-4">
              <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <ShoppingBag className="w-8 h-8 text-gray-400" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Your cart is empty</h3>
              <p className="text-gray-600 text-sm">
                Start shopping to add items to your cart!
              </p>
            </div>
          ) : (
            <div className="h-full overflow-y-auto p-4">
              {/* Cart Items Grid */}
              <div className="grid grid-cols-1 gap-3">
                {cartData.items.map((item) => (
                  <div key={item.product_id} className="flex items-center gap-3 p-3 border border-gray-200 rounded-lg bg-white">
                    {/* Product Image */}
                    <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center flex-shrink-0 overflow-hidden">
                      <img
                        src={getImageSrc(item)}
                        alt={item.name}
                        className="w-full h-full object-cover rounded-lg"
                        onError={handleImageError}
                      />
                    </div>
                    
                    {/* Product Info */}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-gray-900 text-sm leading-tight mb-1">{item.name}</h4>
                      <p className="text-sm text-gray-600 font-medium">{item.price}</p>
                    </div>
                    
                    {/* Quantity Controls */}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                        className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
                      >
                        <Minus className="w-3 h-3 text-gray-600" />
                      </button>
                      <span className="w-8 text-center text-sm font-medium">{item.quantity}</span>
                      <button
                        onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                        className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
                      >
                        <Plus className="w-3 h-3 text-gray-600" />
                      </button>
                    </div>
                    
                    {/* Remove Button */}
                    <button
                      onClick={() => updateQuantity(item.product_id, 0)}
                      className="w-7 h-7 rounded-full bg-red-100 hover:bg-red-200 flex items-center justify-center transition-colors"
                    >
                      <Trash2 className="w-3 h-3 text-red-600" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        {cartData.items.length > 0 && (
          <div className="border-t border-gray-100 p-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-gray-600" />
                <span className="font-medium text-gray-900">Total Items:</span>
              </div>
              <span className="font-semibold text-gray-900">{cartData.total_items}</span>
            </div>
            
            {hasChanges ? (
              <div className="space-y-2">
                <div className="text-sm text-amber-600 bg-amber-50 p-2 rounded-lg">
                  You have unsaved changes. Click "Confirm Changes" to save or "Cancel" to revert.
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={cancelChanges}
                    disabled={isLoading}
                    className="flex-1 px-3 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={confirmChanges}
                    disabled={isLoading}
                    className="flex-1 px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {isLoading ? 'Saving...' : 'Confirm Changes'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={clearCart}
                  disabled={isLoading}
                  className="flex-1 px-3 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                >
                  Clear Cart
                </button>
                <button
                  onClick={handleClose}
                  className="flex-1 px-3 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Continue Shopping
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default CartModal;

