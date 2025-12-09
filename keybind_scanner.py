#!/usr/bin/env python3
"""
Teardown Mod Keybind Scanner

Scans Teardown mod directories for keybind usage in Lua scripts.
"""

import argparse
import csv
import json
import logging
import mimetypes
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Default regex patterns for Teardown input functions
DEFAULT_PATTERNS = [
    r'InputPressed\(\s*["\']([^"\']+)["\']\s*\)',
    r'InputDown\(\s*["\']([^"\']+)["\']\s*\)',
    r'InputReleased\(\s*["\']([^"\']+)["\']\s*\)',
    r'InputValue\(\s*["\']([^"\']+)["\']\s*\)',
]

# File patterns to scan (case-insensitive glob)
FILE_PATTERNS = [
    re.compile(r'^main\.lua$', re.IGNORECASE),
    re.compile(r'^options\.lua$', re.IGNORECASE),
    re.compile(r'^info\.txt$', re.IGNORECASE),
    re.compile(r'^readme.*$', re.IGNORECASE),
]

class KeybindScanner:
    def __init__(self,
                 patterns: List[str] = None,
                 case_insensitive: bool = False,
                 whole_word: bool = False,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 concurrency: int = 4,
                 encoding: str = 'utf-8'):
        self.patterns = patterns or DEFAULT_PATTERNS
        self.case_insensitive = case_insensitive
        self.whole_word = whole_word
        self.max_file_size = max_file_size
        self.concurrency = concurrency
        self.encoding = encoding

        # Compile regex patterns
        flags = re.MULTILINE
        if case_insensitive:
            flags |= re.IGNORECASE

        self.compiled_patterns = []
        for pattern in self.patterns:
            if whole_word:
                pattern = r'\b' + pattern + r'\b'
            self.compiled_patterns.append(re.compile(pattern, flags))

        self.logger = logging.getLogger(__name__)

    def is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely a text file."""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not mime_type.startswith('text/'):
            return False
        # Additional check: try to read first few bytes
        try:
            with open(file_path, 'rb') as f:
                data = f.read(1024)
                # Check for null bytes (binary files often have them)
                if b'\x00' in data:
                    return False
        except Exception:
            return False
        return True

    def should_scan_file(self, file_path: Path) -> bool:
        """Check if file should be scanned based on patterns."""
        filename = file_path.name
        return any(pattern.match(filename) for pattern in FILE_PATTERNS)

    def extract_mod_name(self, dir_path: Path) -> Optional[str]:
        """Extract mod name from info.txt if available."""
        info_file = dir_path / 'info.txt'
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding=self.encoding) as f:
                    for line in f:
                        if line.lower().startswith('name:'):
                            return line.split(':', 1)[1].strip()
            except Exception as e:
                self.logger.warning(f"Error reading {info_file}: {e}")
        return None

    def scan_file(self, file_path: Path) -> List[Dict]:
        """Scan a single file for keybinds."""
        results = []
        try:
            if file_path.stat().st_size > self.max_file_size:
                self.logger.warning(f"Skipping {file_path}: file too large")
                return results

            if not self.is_text_file(file_path):
                self.logger.debug(f"Skipping {file_path}: not a text file")
                return results

            with open(file_path, 'r', encoding=self.encoding) as f:
                content = f.read()

            lines = content.splitlines()
            for line_no, line in enumerate(lines, 1):
                for pattern in self.compiled_patterns:
                    for match in pattern.finditer(line):
                        key_name = match.group(1)
                        # Extract context (up to 100 chars around match)
                        start = max(0, match.start() - 50)
                        end = min(len(line), match.end() + 50)
                        context = line[start:end].strip()

                        results.append({
                            'file_path': str(file_path),
                            'line_number': line_no,
                            'key_name': key_name,
                            'context': context,
                            'matched_text': match.group(0)
                        })

        except Exception as e:
            self.logger.error(f"Error scanning {file_path}: {e}")

        return results

    def scan_directories(self, directories: List[Path], dry_run: bool = False) -> Dict:
        """Scan multiple directories for keybinds."""
        all_results = []
        mod_info = {}

        for dir_path in directories:
            if not dir_path.exists() or not dir_path.is_dir():
                self.logger.warning(f"Directory does not exist: {dir_path}")
                continue

            self.logger.info(f"Scanning directory: {dir_path}")
            mod_name = self.extract_mod_name(dir_path)
            mod_info[str(dir_path)] = mod_name

            if dry_run:
                continue

            # Recursively find files to scan
            for root, dirs, files in os.walk(dir_path):
                root_path = Path(root)
                for file in files:
                    file_path = root_path / file
                    if self.should_scan_file(file_path):
                        self.logger.debug(f"Scanning file: {file_path}")
                        results = self.scan_file(file_path)
                        for result in results:
                            result['mod_name'] = mod_name
                        all_results.extend(results)

        # Aggregate duplicates
        aggregated = self.aggregate_results(all_results)

        return {
            'results': all_results,
            'aggregated': aggregated,
            'mod_info': mod_info,
            'total_files_scanned': len(set(r['file_path'] for r in all_results)),
            'total_matches': len(all_results)
        }

    def aggregate_results(self, results: List[Dict]) -> Dict[str, List[Dict]]:
        """Aggregate results by keybind."""
        aggregated = {}
        for result in results:
            key = result['key_name']
            if key not in aggregated:
                aggregated[key] = []
            aggregated[key].append(result)
        return aggregated

    def save_results(self, scan_data: Dict, output_dir: Path, formats: List[str]):
        """Save results in specified formats."""
        output_dir.mkdir(exist_ok=True)

        if 'json' in formats:
            json_file = output_dir / 'keybinds.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(scan_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved JSON results to {json_file}")

        if 'csv' in formats:
            csv_file = output_dir / 'keybinds.csv'
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                if scan_data['results']:
                    writer = csv.DictWriter(f, fieldnames=scan_data['results'][0].keys())
                    writer.writeheader()
                    writer.writerows(scan_data['results'])
            self.logger.info(f"Saved CSV results to {csv_file}")

def main():
    parser = argparse.ArgumentParser(description='Teardown Mod Keybind Scanner')
    parser.add_argument('directories', nargs='+', help='Directories to scan')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('-f', '--formats', nargs='+', choices=['json', 'csv'], default=['json'],
                        help='Output formats')
    parser.add_argument('-p', '--patterns', nargs='+', help='Custom regex patterns')
    parser.add_argument('-i', '--case-insensitive', action='store_true', help='Case insensitive matching')
    parser.add_argument('-w', '--whole-word', action='store_true', help='Whole word matching')
    parser.add_argument('-s', '--max-file-size', type=int, default=10*1024*1024,
                        help='Maximum file size in bytes')
    parser.add_argument('-c', '--concurrency', type=int, default=4, help='Concurrency level')
    parser.add_argument('-e', '--encoding', default='utf-8', help='File encoding')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose logging')
    parser.add_argument('-l', '--log-file', help='Log file path')

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            *(logging.FileHandler(args.log_file) for _ in [args.log_file] if args.log_file)
        ]
    )

    # Convert directory strings to Paths
    directories = [Path(d) for d in args.directories]

    # Create scanner
    scanner = KeybindScanner(
        patterns=args.patterns,
        case_insensitive=args.case_insensitive,
        whole_word=args.whole_word,
        max_file_size=args.max_file_size,
        concurrency=args.concurrency,
        encoding=args.encoding
    )

    # Scan directories
    scan_data = scanner.scan_directories(directories, dry_run=args.dry_run)

    # Save results
    if not args.dry_run:
        output_dir = Path(args.output)
        scanner.save_results(scan_data, output_dir, args.formats)

    # Print summary
    print(f"Scanned {scan_data['total_files_scanned']} files")
    print(f"Found {scan_data['total_matches']} keybind matches")
    if scan_data['aggregated']:
        print(f"Unique keybinds: {len(scan_data['aggregated'])}")

if __name__ == '__main__':
    main()