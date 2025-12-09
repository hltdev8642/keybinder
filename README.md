# Teardown Mod Keybind Scanner

A tool to detect keybinds used in Teardown game mods by scanning Lua scripts and documentation files.

## Features

- Recursively scans directories for Teardown mod files
- Supports configurable regex patterns for keybind detection
- Outputs results in JSON and/or CSV format
- Extracts mod names from `info.txt` files (`name:` or `name =` fields) or `readme*` files (first header or line)
- Aggregates duplicate keybinds
- Configurable file size limits and encoding
- Dry-run mode for testing
- Comprehensive logging
- **Graphical User Interface (GUI)** for easy operation

## Installation

Requires Python 3.6+

```bash
# Clone or download the script
# No additional dependencies required (uses only standard library)
```

## Usage

### Command Line Interface

```bash
python keybind_scanner.py [OPTIONS] DIRECTORY [DIRECTORY ...]
```

### Graphical User Interface

```bash
python gui.py
```

The GUI provides an intuitive interface for:

- Selecting directories to scan
- Configuring scan options
- Choosing output formats and location
- Running scans with progress indication
- Viewing logs and results

**Persistent Settings**: The GUI remembers your last used directories, output settings, and window position between sessions.

**Persistent Settings**: The GUI remembers your last used directories, output settings, and window position between sessions.

**Note:** The GUI requires Tkinter, which is included with Python by default on most systems.

### Arguments (CLI)

- `DIRECTORY`: One or more directories to scan. If a directory contains subdirectories with mod files (info.txt, readme, or Lua files), each subdirectory will be treated as a separate mod and scanned individually. Otherwise, the directory itself is scanned as a single mod.

### Options (CLI)

- `-o, --output OUTPUT`: Output directory (default: output)
- `-f, --formats FORMATS`: Output formats: json, csv (default: json)
- `-p, --patterns PATTERNS`: Custom regex patterns (replaces defaults)
- `-i, --case-insensitive`: Case insensitive matching
- `-w, --whole-word`: Whole word matching
- `-s, --max-file-size SIZE`: Maximum file size in bytes (default: 10485760)
- `-c, --concurrency CONCURRENCY`: Concurrency level (default: 4)
- `-e, --encoding ENCODING`: File encoding (default: utf-8)
- `-d, --dry-run`: Dry run mode (no actual scanning)
- `-v, --verbose`: Verbose logging
- `-l, --log-file LOG_FILE`: Log file path

## Default Regex Patterns

The scanner uses these default patterns to match Teardown input functions:

- `InputPressed\(\s*["\']([^"\']+)["\']\s*\)`
- `InputDown\(\s*["\']([^"\']+)["\']\s*\)`
- `InputReleased\(\s*["\']([^"\']+)["\']\s*\)`
- `InputValue\(\s*["\']([^"\']+)["\']\s*\)`

## Scanned Files

Only files matching these patterns are scanned (case-insensitive):

- `main.lua`
- `options.lua`
- `info.txt`
- `readme*` (any extension)

## Output Format

### JSON Output

```json
{
  "results": [
    {
      "file_path": "path/to/file.lua",
      "line_number": 42,
      "key_name": "Key_X",
      "context": "if InputPressed(\"Key_X\") then",
      "matched_text": "InputPressed(\"Key_X\")",
      "mod_name": "Sample Mod"
    }
  ],
  "aggregated": {
    "Key_X": [
      {
        "file_path": "path/to/file.lua",
        "line_number": 42,
        "key_name": "Key_X",
        "context": "if InputPressed(\"Key_X\") then",
        "matched_text": "InputPressed(\"Key_X\")",
        "mod_name": "Sample Mod"
      }
    ]
  },
  "mod_info": {
    "/path/to/mod": "Sample Mod"
  },
  "total_files_scanned": 3,
  "total_matches": 5
}
```

### CSV Output

Columns: file_path, line_number, key_name, context, matched_text, mod_name

## Examples

### Basic scan

```bash
python keybind_scanner.py /path/to/mods
```

### Custom patterns and output

```bash
python keybind_scanner.py -p 'InputPressed\("([^"]+)"\)' -f json csv -o results /path/to/mods
```

### Dry run with verbose logging

```bash
python keybind_scanner.py -d -v /path/to/mods
```

## Testing

Run the unit tests:

```bash
python test_scanner.py
```

Sample test data is provided in the `sample_mod/` directory.

## License

MIT License
