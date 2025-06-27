import React from 'react';

const Transcript = ({ data }) => {
  const getSpeakerStyle = (speaker) => {
    switch (speaker.toLowerCase()) {
      case 'agent':
        return 'bg-blue-50 border-l-4 border-l-blue-500';
      case 'customer':
        return 'bg-green-50 border-l-4 border-l-green-500';
      default:
        return 'bg-neutral-50 border-l-4 border-l-neutral-300';
    }
  };

  const handleMessageClick = (timestamp) => {
    console.log('Jump to timestamp:', timestamp);
    // In real app, this would jump to audio position
  };

  return (
    <div className="card p-6 h-96 flex flex-col">
      <h2 className="text-lg font-medium text-neutral-900 mb-4">Transcript</h2>
      
      <div className="flex-1 overflow-y-auto space-y-3">
        {data.map((entry) => (
          <div
            key={entry.id}
            className={`p-3 rounded-lg cursor-pointer hover:shadow-sm transition-shadow ${getSpeakerStyle(entry.speaker)}`}
            onClick={() => handleMessageClick(entry.timestamp)}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-medium text-sm text-neutral-900">
                {entry.speaker}
              </span>
              <span className="text-xs text-neutral-500 font-mono">
                {entry.timestamp}
              </span>
            </div>
            <p className="text-neutral-700 text-sm leading-relaxed">
              {entry.message}
            </p>
          </div>
        ))}
      </div>
      
      {data.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-neutral-500">
          <p>No transcript data available</p>
        </div>
      )}
    </div>
  );
};

export default Transcript;