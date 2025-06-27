import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import SummaryBox from './components/SummaryBox';
import AudioTimeline from './components/AudioTimeline';
import Transcript from './components/Transcript';
import FunctionCallBox from './components/FunctionCallBox';
import LogsViewer from './components/LogsViewer';

function App() {
  const [transcriptData, setTranscriptData] = useState([]);
  const [functionCalls, setFunctionCalls] = useState([]);
  const [logs, setLogs] = useState([]);

  // Sample data - in real app this would come from APIs
  useEffect(() => {
    // Sample transcript data
    setTranscriptData([
      { id: 1, timestamp: '00:02', speaker: 'Agent', message: 'Hello! Thank you for calling Bank of Peril. How can I help you today?' },
      { id: 2, timestamp: '00:05', speaker: 'Customer', message: 'Hi, I need help with my credit card. It was declined this morning.' },
      { id: 3, timestamp: '00:10', speaker: 'Agent', message: 'I understand that must be frustrating. Let me look into your account right away.' },
      { id: 4, timestamp: '00:15', speaker: 'Customer', message: 'Thank you. My card number is 4532-1234-5678-9012.' },
      { id: 5, timestamp: '00:22', speaker: 'Agent', message: 'Perfect, I can see your account now. Let me check the recent transactions.' }
    ]);

    // Sample function calls
    setFunctionCalls([
      { 
        id: 1, 
        timestamp: '00:12', 
        function: 'get_account_info', 
        parameters: { customer_id: 'CUST_12345' },
        result: { status: 'success', account_found: true }
      },
      { 
        id: 2, 
        timestamp: '00:25', 
        function: 'check_recent_transactions', 
        parameters: { account_id: 'ACC_67890', days: 7 },
        result: { status: 'success', transaction_count: 12 }
      }
    ]);

    // Sample logs
    setLogs([
      { timestamp: '00:01:234', level: 'INFO', message: 'Call initiated from +1-555-0123' },
      { timestamp: '00:02:156', level: 'INFO', message: 'VAD detected speech start' },
      { timestamp: '00:05:789', level: 'INFO', message: 'Customer audio processed' },
      { timestamp: '00:12:345', level: 'DEBUG', message: 'Function call: get_account_info' },
      { timestamp: '00:25:678', level: 'DEBUG', message: 'Function call: check_recent_transactions' }
    ]);
  }, []);

  const handleTimelineJump = (time) => {
    console.log('Jump to time:', time);
    // In real app, this would control audio playback
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      <div className="p-8 max-w-7xl mx-auto">
        <Header 
          date="December 15, 2024"
          duration="00:02:45"
          id="CALL_20241215_001"
          status="Completed"
        />
        
        <div className="mt-8">
          <SummaryBox 
            text="Customer contacted support regarding a declined credit card transaction. Agent successfully identified the issue as a temporary hold due to unusual spending pattern and resolved it by removing the hold and providing prevention tips for future transactions."
          />
        </div>

        <div className="mt-8">
          <AudioTimeline 
            duration={165} // 2:45 in seconds
            onJump={handleTimelineJump}
            markers={[
              { time: 12, label: 'Account lookup', type: 'function' },
              { time: 25, label: 'Transaction check', type: 'function' },
              { time: 95, label: 'Issue resolved', type: 'milestone' }
            ]}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
          <Transcript data={transcriptData} />
          <FunctionCallBox calls={functionCalls} />
        </div>

        <div className="mt-8">
          <LogsViewer logs={logs} />
        </div>
      </div>
    </div>
  );
}

export default App;