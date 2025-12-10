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
import xml.etree.ElementTree as ET
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

    def parse_mod_status_xml(self, xml_path: Path) -> Dict[str, bool]:
        """Parse Teardown mods XML file to get mod enabled/disabled status.
        
        Args:
            xml_path: Path to the mods.xml file
            
        Returns:
            Dictionary mapping mod directory names to enabled status (True/False)
        """
        mod_status = {}
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            for mod_elem in root.findall('mod'):
                mod_id = mod_elem.get('id')
                active = mod_elem.get('active', 'false').lower() == 'true'
                
                if mod_id:
                    # Extract mod directory name from id
                    # Remove prefix (steam- or local-) by splitting on first '-' and taking the rest
                    parts = mod_id.split('-', 1)
                    if len(parts) > 1:
                        mod_dir_name = parts[1]
                        mod_status[mod_dir_name] = active
                        self.logger.debug(f"Parsed mod status: {mod_dir_name} -> {'enabled' if active else 'disabled'}")
                    else:
                        self.logger.warning(f"Invalid mod id format: {mod_id}")
                        
        except Exception as e:
            self.logger.error(f"Error parsing mod status XML {xml_path}: {e}")
            
        return mod_status

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
        """Extract mod name from info.txt or readme* files if available."""
        import re
        
        # First, try info.txt
        info_file = dir_path / 'info.txt'
        if info_file.exists():
            self.logger.debug(f"Checking {info_file} for mod name")
            try:
                with open(info_file, 'r', encoding=self.encoding) as f:
                    for line_num, line in enumerate(f, 1):
                        # Match lines like "name: value", "title = value", etc., allowing leading whitespace
                        match = re.match(r'^\s*(?:name|title|mod_name)\s*[=:]\s*(.+)$', line, re.IGNORECASE)
                        if match:
                            name = match.group(1).strip()
                            self.logger.debug(f"Found mod name in {info_file} line {line_num}: {name}")
                            return name
                self.logger.debug(f"No name field found in {info_file}")
            except Exception as e:
                self.logger.warning(f"Error reading {info_file}: {e}")
        else:
            self.logger.debug(f"{info_file} does not exist")

        # If not found in info.txt, try readme files
        for file_path in dir_path.iterdir():
            if file_path.is_file() and file_path.name.lower().startswith('readme'):
                self.logger.debug(f"Checking {file_path} for mod name")
                try:
                    with open(file_path, 'r', encoding=self.encoding) as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line:
                                # Check for markdown header
                                if line.startswith('# '):
                                    name = line[2:].strip()
                                    self.logger.debug(f"Found mod name in {file_path} line {line_num}: {name}")
                                    return name
                                # Or just take the first non-empty line as title
                                name = line
                                self.logger.debug(f"Using first line of {file_path} as mod name: {name}")
                                return name
                except Exception as e:
                    self.logger.warning(f"Error reading {file_path}: {e}")

        self.logger.debug(f"No mod name found for {dir_path}")
        # Fallback to directory name
        fallback_name = dir_path.name
        self.logger.debug(f"Using directory name as fallback: {fallback_name}")
        return fallback_name

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

    def collect_mod_directories(self, directories: List[Path]) -> List[Path]:
        """Collect actual mod directories from input directories.
        
        If an input directory contains subdirectories with info.txt or readme files,
        treat those subdirectories as individual mods. Otherwise, use the input directory.
        """
        mod_dirs = []
        for dir_path in directories:
            if not dir_path.exists() or not dir_path.is_dir():
                continue
            
            # Check if this directory has mod files (info.txt, readme, or lua files)
            has_mod_files = any(
                (dir_path / f).exists() for f in ['info.txt'] + 
                [p.name for p in dir_path.iterdir() if p.is_file() and p.name.lower().startswith('readme')]
            ) or any(
                self.should_scan_file(f) for f in dir_path.rglob('*') if f.is_file()
            )
            
            # Check for subdirectories that look like mods
            sub_mods = []
            for sub_dir in dir_path.iterdir():
                if sub_dir.is_dir():
                    has_sub_mod_files = any(
                        (sub_dir / f).exists() for f in ['info.txt'] + 
                        [p.name for p in sub_dir.iterdir() if p.is_file() and p.name.lower().startswith('readme')]
                    ) or any(
                        self.should_scan_file(f) for f in sub_dir.rglob('*') if f.is_file()
                    )
                    if has_sub_mod_files:
                        sub_mods.append(sub_dir)
            
            if sub_mods:
                # If there are subdirectories that look like mods, use them
                mod_dirs.extend(sub_mods)
                self.logger.info(f"Found {len(sub_mods)} mod subdirectories in {dir_path}")
            elif has_mod_files:
                # Otherwise, use the directory itself
                mod_dirs.append(dir_path)
            else:
                self.logger.warning(f"No mod files found in {dir_path}")
        
        return mod_dirs

    def scan_directories(self, directories: List[Path], dry_run: bool = False, mod_status_xml: Optional[Path] = None) -> Dict:
        """Scan multiple directories for keybinds."""
        # Collect actual mod directories
        mod_dirs = self.collect_mod_directories(directories)
        
        # Parse mod status XML if provided
        mod_status = {}
        if mod_status_xml and mod_status_xml.exists():
            mod_status = self.parse_mod_status_xml(mod_status_xml)
            self.logger.info(f"Loaded status for {len(mod_status)} mods from {mod_status_xml}")
        
        all_results = []
        mod_info = {}

        for dir_path in mod_dirs:
            if not dir_path.exists() or not dir_path.is_dir():
                self.logger.warning(f"Directory does not exist: {dir_path}")
                continue

            self.logger.info(f"Scanning directory: {dir_path}")
            mod_name = self.extract_mod_name(dir_path)
            
            # Get mod status from XML (default to enabled if not found)
            mod_dir_name = dir_path.name
            is_enabled = mod_status.get(mod_dir_name, True)  # Default to True if not in XML
            
            mod_info[str(dir_path)] = {
                'name': mod_name,
                'enabled': is_enabled
            }

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
                            result['mod_enabled'] = is_enabled
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
        """Aggregate results by keybind, deduplicating within each mod."""
        from collections import defaultdict
        
        # Group by mod and keybind to merge multiple occurrences
        mod_key_groups = defaultdict(list)
        for result in results:
            mod_key = (result['mod_name'], result['key_name'])
            mod_key_groups[mod_key].append(result)
        
        # Merge information for each mod-keybind pair
        merged_results = {}
        for (mod_name, key_name), group_results in mod_key_groups.items():
            if len(group_results) == 1:
                # Single occurrence, use as-is
                merged_results[(mod_name, key_name)] = group_results[0]
            else:
                # Multiple occurrences, merge information
                first_result = group_results[0].copy()
                
                # Collect all file paths and line numbers
                all_files = set()
                all_lines = set()
                all_contexts = []
                
                for result in group_results:
                    all_files.add(result['file_path'])
                    all_lines.add(result['line_number'])
                    if result['context'] not in all_contexts:
                        all_contexts.append(result['context'])
                
                # Update the result with merged information
                first_result['file_path'] = '; '.join(sorted(all_files))
                first_result['line_number'] = '; '.join(str(line) for line in sorted(all_lines))
                first_result['context'] = ' | '.join(all_contexts[:3])  # Limit to first 3 contexts
                
                merged_results[(mod_name, key_name)] = first_result
        
        # Now aggregate by keybind
        aggregated = defaultdict(list)
        for result in merged_results.values():
            key = result['key_name']
            aggregated[key].append(result)
        
        return dict(aggregated)

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
    parser.add_argument('-x', '--mod-status-xml', help='Path to Teardown mods.xml file for mod enabled/disabled status')

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
    mod_status_xml = Path(args.mod_status_xml) if args.mod_status_xml else None

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
    scan_data = scanner.scan_directories(directories, dry_run=args.dry_run, mod_status_xml=mod_status_xml)

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