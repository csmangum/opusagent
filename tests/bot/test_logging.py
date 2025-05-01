import json
import os
from datetime import datetime
from typing import Dict, Any

class PerformanceTestLogger:
    def __init__(self, log_dir: str = "test_logs"):
        self.log_dir = log_dir
        self.current_test = None
        self.test_start_time = None
        self.results = {}
        
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)
    
    def start_test(self, test_name: str):
        """Start recording a new test."""
        self.current_test = test_name
        self.test_start_time = datetime.now()
        self.results[test_name] = {
            "start_time": self.test_start_time.isoformat(),
            "metrics": {}
        }
    
    def log_metric(self, metric_name: str, value: Any, unit: str = None):
        """Log a metric for the current test."""
        if not self.current_test:
            raise ValueError("No test is currently running")
        
        metric_data = {"value": value}
        if unit:
            metric_data["unit"] = unit
        
        self.results[self.current_test]["metrics"][metric_name] = metric_data
    
    def end_test(self):
        """End the current test and save results."""
        if not self.current_test:
            raise ValueError("No test is currently running")
        
        end_time = datetime.now()
        self.results[self.current_test]["end_time"] = end_time.isoformat()
        self.results[self.current_test]["duration_seconds"] = (end_time - self.test_start_time).total_seconds()
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.log_dir, f"performance_test_{timestamp}.json")
        
        with open(log_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        self.current_test = None
        self.test_start_time = None
        return log_file

# Create a global logger instance
logger = PerformanceTestLogger() 