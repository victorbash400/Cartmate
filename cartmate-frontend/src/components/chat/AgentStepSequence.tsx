import React from 'react';
import { Check, Loader2 } from 'lucide-react';

export interface AgentStep {
  id: string;
  type: 'calling' | 'processing' | 'success' | 'error';
  agentName: string;
  message: string;
  timestamp?: Date;
}

interface AgentStepSequenceProps {
  steps: AgentStep[];
  isActive?: boolean;
}

const AgentStepSequence: React.FC<AgentStepSequenceProps> = ({ steps, isActive = false }) => {
  const getStepIcon = (step: AgentStep, index: number) => {
    const isLastStep = index === steps.length - 1;
    const hasNextStep = index < steps.length - 1;
    
    // Check if the entire process is complete (last step in sequence is success)
    const lastStep = steps[steps.length - 1];
    const isProcessComplete = lastStep && lastStep.type === 'success';
    
    // If process is complete, all steps should show check marks
    if (isProcessComplete) {
      return <Check size={14} className="text-black" />;
    }
    
    // If there's a next step, this step is done (show check)
    if (hasNextStep) {
      return <Check size={14} className="text-black" />;
    }
    
    // If this is the last step and it's processing/calling, show spinner
    if (isLastStep && (step.type === 'processing' || step.type === 'calling')) {
      return <Loader2 size={14} className="text-black animate-spin" />;
    }
    
    // If this is the last step and it's error, show error
    if (isLastStep && step.type === 'error') {
      return <div className="w-3 h-3 rounded-full bg-red-500 flex items-center justify-center">
        <span className="text-white text-xs font-bold">!</span>
      </div>;
    }
    
    // Default: gray circle
    return <div className="w-3 h-3 rounded-full bg-gray-300"></div>;
  };

  const getStepStatus = (step: AgentStep, index: number) => {
    if (step.type === 'error') {
      return 'text-red-700';
    } else {
      return 'text-black';
    }
  };

  return (
    <div className="border-2 border-black rounded-lg p-3 mb-2 bg-white">
      <div className="flex flex-col">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-start gap-3">
            {/* Step icon with connecting line */}
            <div className="flex flex-col items-center pt-0.5">
              <div className="flex-shrink-0">
                {getStepIcon(step, index)}
              </div>
              {/* Connecting line to next step */}
              {index < steps.length - 1 && (
                <div className="w-px h-6 bg-gray-300 mt-2"></div>
              )}
            </div>
            
            {/* Step content */}
            <div className="flex-1 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-gray-900">{step.agentName}</span>
                <span className="text-gray-400">•</span>
                <span className={`text-xs ${getStepStatus(step, index)}`}>{step.message}</span>
              </div>
              
              {/* Step number */}
              <span className="text-xs text-gray-500 font-mono">{index + 1}/{steps.length}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentStepSequence;
