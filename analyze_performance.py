"""
Script to analyze and visualize performance test results from the SQLite database.
Generates various charts to track performance metrics over time.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from typing import List, Dict, Optional

# Configure matplotlib style
plt.style.use('seaborn')
sns.set_palette("husl")

# Database configuration
DB_FILE = Path("test_results") / "performance_test.db"
OUTPUT_DIR = Path("test_results") / "charts"
OUTPUT_DIR.mkdir(exist_ok=True)

def get_test_results() -> pd.DataFrame:
    """Retrieve test results from the database."""
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT 
        id,
        test_name,
        timestamp,
        status,
        average_chunks_per_second,
        average_kb_per_second,
        total_chunks_sent,
        total_bytes_sent,
        error_message
    FROM test_results
    ORDER BY timestamp
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def get_test_logs(test_result_id: int) -> pd.DataFrame:
    """Retrieve logs for a specific test result."""
    conn = sqlite3.connect(DB_FILE)
    query = """
    SELECT 
        timestamp,
        level,
        message
    FROM test_logs
    WHERE test_result_id = ?
    ORDER BY timestamp
    """
    df = pd.read_sql_query(query, conn, params=(test_result_id,))
    conn.close()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    return df

def plot_throughput_over_time(df: pd.DataFrame):
    """Plot audio throughput metrics over time."""
    plt.figure(figsize=(12, 6))
    
    # Filter for audio sending tests
    audio_tests = df[df['test_name'] == 'test_audio_sending_throughput']
    
    # Plot chunks per second
    plt.subplot(2, 1, 1)
    plt.plot(audio_tests['timestamp'], audio_tests['average_chunks_per_second'], 
             marker='o', label='Chunks per Second')
    plt.title('Audio Sending Throughput Over Time')
    plt.ylabel('Chunks per Second')
    plt.grid(True)
    plt.legend()
    
    # Plot KB per second
    plt.subplot(2, 1, 2)
    plt.plot(audio_tests['timestamp'], audio_tests['average_kb_per_second'], 
             marker='o', color='orange', label='KB per Second')
    plt.ylabel('KB per Second')
    plt.xlabel('Date')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'throughput_over_time.png')
    plt.close()

def plot_success_rate(df: pd.DataFrame):
    """Plot test success rate over time."""
    plt.figure(figsize=(10, 6))
    
    # Calculate success rate by day
    df['date'] = df['timestamp'].dt.date
    daily_stats = df.groupby('date')['status'].value_counts().unstack().fillna(0)
    daily_stats['success_rate'] = daily_stats['completed'] / (daily_stats['completed'] + daily_stats['failed'])
    
    plt.plot(daily_stats.index, daily_stats['success_rate'], 
             marker='o', color='green', label='Success Rate')
    plt.title('Test Success Rate Over Time')
    plt.ylabel('Success Rate')
    plt.xlabel('Date')
    plt.grid(True)
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'success_rate.png')
    plt.close()

def plot_error_analysis(df: pd.DataFrame):
    """Plot error analysis and trends."""
    plt.figure(figsize=(12, 6))
    
    # Filter for failed tests
    failed_tests = df[df['status'] == 'failed']
    
    if not failed_tests.empty:
        # Plot error frequency over time
        plt.subplot(1, 2, 1)
        error_counts = failed_tests.groupby(failed_tests['timestamp'].dt.date).size()
        error_counts.plot(kind='bar', color='red')
        plt.title('Error Frequency Over Time')
        plt.xlabel('Date')
        plt.ylabel('Number of Errors')
        plt.xticks(rotation=45)
        
        # Plot error types
        plt.subplot(1, 2, 2)
        error_types = failed_tests['error_message'].value_counts().head(5)
        error_types.plot(kind='pie', autopct='%1.1f%%')
        plt.title('Top 5 Error Types')
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'error_analysis.png')
        plt.close()

def plot_performance_distribution(df: pd.DataFrame):
    """Plot distribution of performance metrics."""
    plt.figure(figsize=(12, 6))
    
    # Filter for successful audio tests
    audio_tests = df[(df['test_name'] == 'test_audio_sending_throughput') & 
                    (df['status'] == 'completed')]
    
    if not audio_tests.empty:
        # Plot distribution of chunks per second
        plt.subplot(1, 2, 1)
        sns.histplot(audio_tests['average_chunks_per_second'], kde=True)
        plt.title('Distribution of Chunks per Second')
        plt.xlabel('Chunks per Second')
        
        # Plot distribution of KB per second
        plt.subplot(1, 2, 2)
        sns.histplot(audio_tests['average_kb_per_second'], kde=True)
        plt.title('Distribution of KB per Second')
        plt.xlabel('KB per Second')
        
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / 'performance_distribution.png')
        plt.close()

def generate_summary_report(df: pd.DataFrame):
    """Generate a summary report of performance metrics."""
    report_path = OUTPUT_DIR / 'performance_summary.txt'
    
    with open(report_path, 'w') as f:
        f.write("Performance Test Summary Report\n")
        f.write("=============================\n\n")
        
        # Overall statistics
        f.write("Overall Statistics:\n")
        f.write(f"Total test runs: {len(df)}\n")
        f.write(f"Successful runs: {len(df[df['status'] == 'completed'])}\n")
        f.write(f"Failed runs: {len(df[df['status'] == 'failed'])}\n")
        f.write(f"Success rate: {(len(df[df['status'] == 'completed']) / len(df) * 100):.2f}%\n\n")
        
        # Audio test statistics
        audio_tests = df[df['test_name'] == 'test_audio_sending_throughput']
        if not audio_tests.empty:
            f.write("Audio Sending Performance:\n")
            f.write(f"Average chunks per second: {audio_tests['average_chunks_per_second'].mean():.2f}\n")
            f.write(f"Average KB per second: {audio_tests['average_kb_per_second'].mean():.2f}\n")
            f.write(f"Best performance (chunks/s): {audio_tests['average_chunks_per_second'].max():.2f}\n")
            f.write(f"Worst performance (chunks/s): {audio_tests['average_chunks_per_second'].min():.2f}\n\n")
        
        # Error analysis
        failed_tests = df[df['status'] == 'failed']
        if not failed_tests.empty:
            f.write("Error Analysis:\n")
            error_counts = failed_tests['error_message'].value_counts()
            for error, count in error_counts.items():
                f.write(f"{error}: {count} occurrences\n")

def main():
    """Main function to generate all charts and reports."""
    print("Analyzing performance test results...")
    
    # Get test results
    df = get_test_results()
    
    if df.empty:
        print("No test results found in the database.")
        return
    
    # Generate charts
    print("Generating charts...")
    plot_throughput_over_time(df)
    plot_success_rate(df)
    plot_error_analysis(df)
    plot_performance_distribution(df)
    
    # Generate summary report
    print("Generating summary report...")
    generate_summary_report(df)
    
    print(f"Analysis complete. Results saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 