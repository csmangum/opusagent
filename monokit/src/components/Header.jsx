import React from 'react';

const Header = ({ date, duration, id, status }) => {
  const getStatusColor = (status) => {
    switch (status.toLowerCase()) {
      case 'completed': return 'text-green-600 bg-green-100';
      case 'in-progress': return 'text-blue-600 bg-blue-100';
      case 'failed': return 'text-red-600 bg-red-100';
      default: return 'text-neutral-600 bg-neutral-100';
    }
  };

  return (
    <div className="card p-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-semibold text-neutral-900 mb-2">Call Analysis</h1>
          <div className="space-y-1 text-sm text-neutral-600">
            <p><span className="font-medium">Date:</span> {date}</p>
            <p><span className="font-medium">Duration:</span> {duration}</p>
            <p><span className="font-medium">Call ID:</span> {id}</p>
          </div>
        </div>
        <div className="text-right">
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(status)}`}>
            {status}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header;