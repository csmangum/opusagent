import React, { useState } from 'react';

const AudioTimeline = ({ duration, onJump, markers = [] }) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleTimelineClick = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const clickPosition = (event.clientX - rect.left) / rect.width;
    const newTime = Math.floor(clickPosition * duration);
    setCurrentTime(newTime);
    onJump(newTime);
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
    // In real app, this would control actual audio playback
  };

  const getMarkerColor = (type) => {
    switch (type) {
      case 'function': return 'bg-blue-500';
      case 'milestone': return 'bg-green-500';
      default: return 'bg-neutral-500';
    }
  };

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-neutral-900">Audio Timeline</h2>
        <div className="flex items-center space-x-4">
          <button
            onClick={togglePlayback}
            className="btn-secondary flex items-center space-x-2"
          >
            <div className={`w-0 h-0 ${isPlaying ? 'border-l-8 border-l-neutral-600 border-t-4 border-t-transparent border-b-4 border-b-transparent' : 'border-l-8 border-l-neutral-600 border-t-4 border-t-transparent border-b-4 border-b-transparent'}`} />
            <span>{isPlaying ? 'Pause' : 'Play'}</span>
          </button>
          <span className="text-sm text-neutral-600">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
        </div>
      </div>

      {/* Waveform visualization placeholder */}
      <div className="relative mb-4">
        <div className="h-24 bg-neutral-100 rounded border overflow-hidden">
          {/* Simple waveform visualization */}
          <div className="flex items-end h-full px-2">
            {Array.from({ length: 50 }, (_, i) => (
              <div
                key={i}
                className="bg-neutral-400 mx-0.5 rounded-t"
                style={{
                  height: `${Math.random() * 60 + 20}%`,
                  width: '2%'
                }}
              />
            ))}
          </div>
          
          {/* Progress indicator */}
          <div
            className="absolute top-0 bottom-0 w-0.5 bg-neutral-900"
            style={{ left: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        {/* Timeline markers */}
        {markers.map((marker, index) => (
          <div
            key={index}
            className="absolute top-0 bottom-0 w-0.5"
            style={{ left: `${(marker.time / duration) * 100}%` }}
          >
            <div className={`w-0.5 h-full ${getMarkerColor(marker.type)}`} />
            <div className="absolute top-full mt-1 transform -translate-x-1/2 text-xs text-neutral-600 bg-white px-1 py-0.5 rounded border shadow-sm whitespace-nowrap">
              {marker.label}
            </div>
          </div>
        ))}
      </div>

      {/* Timeline scrubber */}
      <div
        className="relative h-2 bg-neutral-200 rounded cursor-pointer"
        onClick={handleTimelineClick}
      >
        <div
          className="absolute top-0 left-0 h-full bg-neutral-900 rounded"
          style={{ width: `${(currentTime / duration) * 100}%` }}
        />
      </div>
    </div>
  );
};

export default AudioTimeline;