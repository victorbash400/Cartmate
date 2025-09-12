import React, { useState } from 'react';
import { Check, CreditCard, MapPin, Mail } from 'lucide-react';

interface CheckoutFormProps {
  message: string;
  formData: {
    email: string;
    address: {
      street_address: string;
      city: string;
      state: string;
      country: string;
      zip_code: string;
    };
    credit_card: {
      number: string;
      cvv: string;
      expiration_year: string;
      expiration_month: string;
    };
  };
  onSubmit: (data: any) => void;
}

export const CheckoutForm: React.FC<CheckoutFormProps> = ({ message, formData, onSubmit }) => {
  const [form, setForm] = useState({
    email: formData.email,
    address: {
      street_address: formData.address.street_address,
      city: formData.address.city,
      state: formData.address.state,
      country: formData.address.country,
      zip_code: formData.address.zip_code,
    },
    credit_card: {
      number: formData.credit_card.number || "4111111111111111", // Demo card number
      cvv: formData.credit_card.cvv || "123", // Demo CVV
      expiration_year: formData.credit_card.expiration_year || "2025", // Demo expiration
      expiration_month: formData.credit_card.expiration_month || "12", // Demo expiration
    }
  });

  const [isSubmitting, setIsSubmitting] = useState(false);

  const fillDemoData = () => {
    setForm({
      email: "demo@example.com",
      address: {
        street_address: "123 Demo Street",
        city: "Demo City",
        state: "DC",
        country: "USA",
        zip_code: "12345",
      },
      credit_card: {
        number: "4111111111111111",
        cvv: "123",
        expiration_year: "2025",
        expiration_month: "12",
      }
    });
  };

  const handleInputChange = (field: string, value: string, subField?: string) => {
    setForm(prev => {
      if (subField) {
        return {
          ...prev,
          [field]: {
            ...prev[field as keyof typeof prev],
            [subField]: value
          }
        };
      }
      return {
        ...prev,
        [field]: value
      };
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await onSubmit({
        email: form.email,
        address: form.address,
        credit_card: form.credit_card
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-300 p-4 max-w-lg mx-auto">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-6 h-6 bg-gray-100 rounded-full flex items-center justify-center">
          <CreditCard className="w-3 h-3 text-gray-600" />
        </div>
        <h3 className="text-sm font-medium text-gray-900">Checkout</h3>
      </div>
      
      <p className="text-gray-600 text-sm mb-4">{message}</p>
      
      <div className="mb-3">
        <button
          type="button"
          onClick={fillDemoData}
          className="text-xs text-gray-500 hover:text-gray-700 underline"
        >
          Fill Demo Data
        </button>
      </div>
      
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Email Section */}
        <div className="space-y-1">
          <label className="flex items-center gap-1 text-xs font-medium text-gray-700">
            <Mail className="w-3 h-3" />
            Email
          </label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => handleInputChange('email', e.target.value)}
            className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
            placeholder="your.email@example.com"
            required
          />
        </div>

        {/* Address Section */}
        <div className="space-y-2">
          <label className="flex items-center gap-1 text-xs font-medium text-gray-700">
            <MapPin className="w-3 h-3" />
            Address
          </label>
          
          <div className="space-y-2">
            <input
              type="text"
              value={form.address.street_address}
              onChange={(e) => handleInputChange('address', e.target.value, 'street_address')}
              className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
              placeholder="Street Address"
              required
            />
            
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={form.address.city}
                onChange={(e) => handleInputChange('address', e.target.value, 'city')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="City"
                required
              />
              <input
                type="text"
                value={form.address.state}
                onChange={(e) => handleInputChange('address', e.target.value, 'state')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="State"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={form.address.country}
                onChange={(e) => handleInputChange('address', e.target.value, 'country')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="Country"
                required
              />
              <input
                type="text"
                value={form.address.zip_code}
                onChange={(e) => handleInputChange('address', e.target.value, 'zip_code')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="ZIP"
                required
              />
            </div>
          </div>
        </div>

        {/* Credit Card Section */}
        <div className="space-y-2">
          <label className="flex items-center gap-1 text-xs font-medium text-gray-700">
            <CreditCard className="w-3 h-3" />
            Payment
          </label>
          
          <div className="space-y-2">
            <input
              type="text"
              value={form.credit_card.number}
              onChange={(e) => handleInputChange('credit_card', e.target.value, 'number')}
              className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
              placeholder="Card Number (4111 1111 1111 1111 for demo)"
              required
            />
            
            <div className="grid grid-cols-3 gap-2">
              <input
                type="text"
                value={form.credit_card.expiration_month}
                onChange={(e) => handleInputChange('credit_card', e.target.value, 'expiration_month')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="MM"
                maxLength={2}
                required
              />
              <input
                type="text"
                value={form.credit_card.expiration_year}
                onChange={(e) => handleInputChange('credit_card', e.target.value, 'expiration_year')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="YYYY"
                maxLength={4}
                required
              />
              <input
                type="text"
                value={form.credit_card.cvv}
                onChange={(e) => handleInputChange('credit_card', e.target.value, 'cvv')}
                className="w-full px-2 py-1.5 bg-white border border-gray-300 rounded text-sm text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-gray-500 focus:border-transparent"
                placeholder="CVV"
                maxLength={4}
                required
              />
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="pt-2">
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-gray-900 text-white py-2 px-3 rounded text-sm hover:bg-gray-800 focus:outline-none focus:ring-1 focus:ring-gray-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isSubmitting ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Processing...
              </>
            ) : (
              <>
                <Check className="w-3 h-3" />
                Complete Checkout
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
