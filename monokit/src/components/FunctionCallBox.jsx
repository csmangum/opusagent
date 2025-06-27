import React, { useState } from 'react';

const FunctionCallBox = ({ calls }) => {
  const [expandedCall, setExpandedCall] = useState(null);

  const toggleExpanded = (callId) => {
    setExpandedCall(expandedCall === callId ? null : callId);
  };

  const formatJson = (obj) => {
    return JSON.stringify(obj, null, 2);
  };

  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'success': return 'text-green-600';
      case 'error': return 'text-red-600';
      case 'pending': return 'text-yellow-600';
      default: return 'text-neutral-600';
    }
  };

  return (
    <div className="card p-6 h-96 flex flex-col">
      <h2 className="text-lg font-medium text-neutral-900 mb-4">Function Calls</h2>
      
      <div className="flex-1 overflow-y-auto space-y-3">
        {calls.map((call) => (
          <div key={call.id} className="border border-neutral-200 rounded-lg">
            <div
              className="p-3 cursor-pointer hover:bg-neutral-50 transition-colors"
              onClick={() => toggleExpanded(call.id)}
            >
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center space-x-2">
                  <code className="text-sm font-mono bg-neutral-100 px-2 py-1 rounded">
                    {call.function}
                  </code>
                  <span className={`text-xs font-medium ${getStatusColor(call.result?.status)}`}>
                    {call.result?.status || 'unknown'}
                  </span>
                </div>
                <span className="text-xs text-neutral-500 font-mono">
                  {call.timestamp}
                </span>
              </div>
              
              <div className="flex items-center justify-between">
                <span className="text-xs text-neutral-600">
                  {Object.keys(call.parameters || {}).length} parameters
                </span>
                <div className="text-neutral-400">
                  {expandedCall === call.id ? '−' : '+'}
                </div>
              </div>
            </div>
            
            {expandedCall === call.id && (
              <div className="px-3 pb-3 border-t border-neutral-100">
                <div className="mt-3 space-y-3">
                  <div>
                    <h4 className="text-xs font-medium text-neutral-900 mb-1">Parameters:</h4>
                    <pre className="text-xs bg-neutral-50 p-2 rounded border overflow-x-auto">
                      {formatJson(call.parameters)}
                    </pre>
                  </div>
                  
                  {call.result && (
                    <div>
                      <h4 className="text-xs font-medium text-neutral-900 mb-1">Result:</h4>
                      <pre className="text-xs bg-neutral-50 p-2 rounded border overflow-x-auto">
                        {formatJson(call.result)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {calls.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-neutral-500">
          <p>No function calls recorded</p>
        </div>
      )}
    </div>
  );
};

export default FunctionCallBox;