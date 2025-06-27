import React, { useState } from 'react';

const LogsViewer = ({ logs = [] }) => {
  const [filterLevel, setFilterLevel] = useState('ALL');

  const getLevelColor = (level) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'text-red-600 bg-red-50';
      case 'WARN': 
      case 'WARNING': return 'text-yellow-600 bg-yellow-50';
      case 'INFO': return 'text-blue-600 bg-blue-50';
      case 'DEBUG': return 'text-neutral-600 bg-neutral-50';
      default: return 'text-neutral-600 bg-neutral-50';
    }
  };

  const filteredLogs = filterLevel === 'ALL' 
    ? logs 
    : logs.filter(log => log.level.toUpperCase() === filterLevel);

  const levels = ['ALL', 'ERROR', 'WARN', 'INFO', 'DEBUG'];

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-medium text-neutral-900">System Logs</h2>
        
        <div className="flex items-center space-x-2">
          <span className="text-sm text-neutral-600">Filter:</span>
          <select
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="border border-neutral-300 rounded px-2 py-1 text-sm bg-white"
          >
            {levels.map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="h-64 overflow-y-auto border border-neutral-200 rounded bg-neutral-50">
        <div className="p-3 space-y-2">
          {filteredLogs.map((log, index) => (
            <div key={index} className="flex items-start space-x-3 text-sm">
              <span className="font-mono text-xs text-neutral-500 shrink-0 w-20">
                {log.timestamp}
              </span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${getLevelColor(log.level)}`}>
                {log.level}
              </span>
              <span className="text-neutral-700 flex-1 leading-relaxed">
                {log.message}
              </span>
            </div>
          ))}
        </div>
        
        {filteredLogs.length === 0 && (
          <div className="h-full flex items-center justify-center text-neutral-500">
            <p>No logs to display</p>
          </div>
        )}
      </div>
      
      <div className="mt-3 text-xs text-neutral-500 flex justify-between">
        <span>Showing {filteredLogs.length} of {logs.length} entries</span>
        <span>Auto-refresh: OFF</span>
      </div>
    </div>
  );
};

export default LogsViewer;