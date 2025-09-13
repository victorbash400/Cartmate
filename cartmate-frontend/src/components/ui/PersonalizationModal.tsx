import React, { useState, useRef } from 'react';
import { X, Upload, Camera, DollarSign, Palette, Save } from 'lucide-react';

interface PersonalizationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: PersonalizationData) => void;
}

interface PersonalizationData {
  image?: File;
  stylePreferences: string;
  budgetRange: {
    min: number;
    max: number;
  };
}

const PersonalizationModal: React.FC<PersonalizationModalProps> = ({ isOpen, onClose, onSave }) => {
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [stylePreferences, setStylePreferences] = useState('');
  const [budgetRange, setBudgetRange] = useState({ min: 50, max: 200 });
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleImageUpload = (file: File) => {
    if (file && file.type.startsWith('image/')) {
      setImage(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setImagePreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    handleImageUpload(file);
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleImageUpload(file);
    }
  };

  const handleSave = async () => {
    setIsLoading(true);
    try {
      const data: PersonalizationData = {
        ...(image && { image }),
        stylePreferences,
        budgetRange
      };
      await onSave(data);
      onClose();
    } catch (error) {
      console.error('Error saving personalization data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setImage(null);
    setImagePreview(null);
    setStylePreferences('');
    setBudgetRange({ min: 50, max: 200 });
    onClose();
  };

  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4 pointer-events-none">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-2xl mx-auto transform transition-all duration-300 scale-100 pointer-events-auto border border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-black rounded-full flex items-center justify-center">
              <span className="text-white text-xs font-bold">P</span>
            </div>
            <h2 className="text-base font-medium text-gray-900">Personalize</h2>
          </div>
          <button
            onClick={handleClose}
            className="w-5 h-5 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center transition-colors"
          >
            <X className="w-3 h-3 text-gray-600" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <div className="grid grid-cols-2 gap-4">
            {/* Left Column - Image Upload */}
            <div className="space-y-3">
              <label className="text-xs font-medium text-gray-700 flex items-center gap-1">
                <Camera className="w-3 h-3" />
                Upload Photo (Optional)
              </label>
              <div
                className={`border-2 border-dashed rounded-lg p-3 text-center transition-colors cursor-pointer ${
                  isDragging 
                    ? 'border-gray-400 bg-gray-50' 
                    : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  onChange={handleFileInput}
                  className="hidden"
                />
                
                {imagePreview ? (
                  <div className="space-y-2">
                    <img
                      src={imagePreview}
                      alt="Preview"
                      className="w-16 h-16 rounded-full object-cover mx-auto"
                    />
                    <p className="text-xs text-gray-600">Click to change</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center mx-auto">
                      <Upload className="w-4 h-4 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-xs text-gray-600">
                        <span className="text-gray-700 font-medium">Click to browse</span>
                      </p>
                      <p className="text-xs text-gray-500">JPG, PNG</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column - Style & Budget */}
            <div className="space-y-3">
              {/* Style Preferences */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-700 flex items-center gap-1">
                  <Palette className="w-3 h-3" />
                  Style Preferences
                </label>
                <textarea
                  value={stylePreferences}
                  onChange={(e) => setStylePreferences(e.target.value)}
                  placeholder="casual, minimalist, bohemian..."
                  className="w-full p-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-gray-500 focus:border-transparent resize-none text-xs"
                  rows={2}
                />
              </div>

              {/* Budget Range */}
              <div className="space-y-2">
                <label className="text-xs font-medium text-gray-700 flex items-center gap-1">
                  <DollarSign className="w-3 h-3" />
                  Budget Range (USD)
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Min</label>
                    <input
                      type="number"
                      value={budgetRange.min}
                      onChange={(e) => setBudgetRange(prev => ({ ...prev, min: parseInt(e.target.value) || 0 }))}
                      className="w-full p-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-gray-500 focus:border-transparent text-xs"
                      min="0"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 block mb-1">Max</label>
                    <input
                      type="number"
                      value={budgetRange.max}
                      onChange={(e) => setBudgetRange(prev => ({ ...prev, max: parseInt(e.target.value) || 0 }))}
                      className="w-full p-2 border border-gray-300 rounded-lg focus:ring-1 focus:ring-gray-500 focus:border-transparent text-xs"
                      min="0"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-4 border-t border-gray-100">
          <button
            onClick={handleClose}
            className="flex-1 px-3 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading}
            className="flex-1 px-3 py-2 bg-black hover:bg-gray-800 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-1"
          >
            {isLoading ? (
              <>
                <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-3 h-3" />
                Save
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default PersonalizationModal;
