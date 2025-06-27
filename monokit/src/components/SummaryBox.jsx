import React from 'react';

const SummaryBox = ({ text, title = "Call Summary" }) => {
  return (
    <div className="card p-6">
      <h2 className="text-lg font-medium text-neutral-900 mb-3">{title}</h2>
      <p className="text-neutral-700 leading-relaxed">{text}</p>
    </div>
  );
};

export default SummaryBox;