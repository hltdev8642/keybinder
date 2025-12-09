#!/usr/bin/env python3
"""
Unit tests for keybind scanner
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from keybind_scanner import KeybindScanner


class TestKeybindScanner(unittest.TestCase):
    def setUp(self):
        self.scanner = KeybindScanner()

    def test_default_patterns(self):
        """Test default regex patterns."""
        test_content = '''
        if InputPressed("Key_X") then
            do_something()
        end

        if InputDown("Key_C") then
            continuous_action()
        end

        if InputReleased("interact") then
            release_action()
        end

        local value = InputValue("mousewheel")
        '''

        # Mock file scanning
        results = []
        lines = test_content.splitlines()
        for line_no, line in enumerate(lines, 1):
            for pattern in self.scanner.compiled_patterns:
                for match in pattern.finditer(line):
                    results.append({
                        'file_path': 'test.lua',
                        'line_number': line_no,
                        'key_name': match.group(1),
                        'context': line.strip(),
                        'matched_text': match.group(0)
                    })

        self.assertEqual(len(results), 4)
        key_names = [r['key_name'] for r in results]
        self.assertIn('Key_X', key_names)
        self.assertIn('Key_C', key_names)
        self.assertIn('interact', key_names)
        self.assertIn('mousewheel', key_names)

    def test_file_filtering(self):
        """Test file pattern matching."""
        test_files = [
            'main.lua',
            'MAIN.LUA',
            'options.lua',
            'info.txt',
            'readme.txt',
            'readme.md',
            'README',
            'script.lua',  # Should not match
            'data.json',   # Should not match
        ]

        for file in test_files:
            path = Path(file)
            should_scan = self.scanner.should_scan_file(path)
            if file.lower() in ['main.lua', 'options.lua', 'info.txt'] or file.lower().startswith('readme'):
                self.assertTrue(should_scan, f"Should scan {file}")
            else:
                self.assertFalse(should_scan, f"Should not scan {file}")

    def test_mod_name_extraction(self):
        """Test mod name extraction from info.txt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mod_dir = Path(tmpdir) / 'test_mod'
            mod_dir.mkdir()

            # Create info.txt
            info_file = mod_dir / 'info.txt'
            info_file.write_text('name: Test Mod\nversion: 1.0\n')

            mod_name = self.scanner.extract_mod_name(mod_dir)
            self.assertEqual(mod_name, 'Test Mod')

    def test_json_output(self):
        """Test JSON output format."""
        test_data = {
            'results': [
                {
                    'file_path': 'test.lua',
                    'line_number': 1,
                    'key_name': 'Key_X',
                    'context': 'if InputPressed("Key_X") then',
                    'matched_text': 'InputPressed("Key_X")',
                    'mod_name': 'Test Mod'
                }
            ],
            'aggregated': {'Key_X': [{'key_name': 'Key_X'}]},
            'mod_info': {'/path': 'Test Mod'},
            'total_files_scanned': 1,
            'total_matches': 1
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'output'
            self.scanner.save_results(test_data, output_dir, ['json'])

            json_file = output_dir / 'keybinds.json'
            self.assertTrue(json_file.exists())

            with open(json_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
                self.assertEqual(loaded_data, test_data)

    def test_csv_output(self):
        """Test CSV output format."""
        test_data = {
            'results': [
                {
                    'file_path': 'test.lua',
                    'line_number': 1,
                    'key_name': 'Key_X',
                    'context': 'if InputPressed("Key_X") then',
                    'matched_text': 'InputPressed("Key_X")',
                    'mod_name': 'Test Mod'
                }
            ],
            'aggregated': {},
            'mod_info': {},
            'total_files_scanned': 1,
            'total_matches': 1
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'output'
            self.scanner.save_results(test_data, output_dir, ['csv'])

            csv_file = output_dir / 'keybinds.csv'
            self.assertTrue(csv_file.exists())

            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = list(csv.DictReader(f))
                self.assertEqual(len(reader), 1)
                self.assertEqual(reader[0]['key_name'], 'Key_X')


if __name__ == '__main__':
    unittest.main()