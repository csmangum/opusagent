import argparse
import os
import re
from datetime import datetime

# Regex to match the timestamp at the start of each log line
TIMESTAMP_REGEX = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})')


def parse_log_file(filepath):
    lines = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            match = TIMESTAMP_REGEX.match(line)
            if match:
                timestamp_str = match.group(1)
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                except ValueError:
                    continue  # skip lines with invalid timestamp
                lines.append((timestamp, line.rstrip()))
    return lines


def main():
    parser = argparse.ArgumentParser(description='Combine and sort log files by timestamp, outputting only the original log lines (no label).')
    parser.add_argument('logfiles', nargs='+', help='Paths to log files to combine')
    parser.add_argument('-o', '--output', required=True, help='Output file for combined logs')
    args = parser.parse_args()

    all_lines = []
    for logfile in args.logfiles:
        all_lines.extend(parse_log_file(logfile))

    # Sort all lines by timestamp
    all_lines.sort(key=lambda x: x[0])

    with open(args.output, 'w', encoding='utf-8') as out:
        for _, line in all_lines:
            out.write(f'{line}\n')

    print(f'Combined log written to {args.output}')


if __name__ == '__main__':
    main() 