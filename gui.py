#!/usr/bin/env python3
"""
GUI for Teardown Mod Keybind Scanner
"""

import json
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from keybind_scanner import KeybindScanner


class KeybindScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Teardown Mod Keybind Scanner")
        self.root.geometry("800x600")

        # Scanner instance
        self.scanner = None
        self.scan_thread = None

        # UI variables
        self.directories = []
        self.output_dir = tk.StringVar(value="output")
        self.custom_patterns = tk.StringVar()
        self.case_insensitive = tk.BooleanVar()
        self.whole_word = tk.BooleanVar()
        self.json_format = tk.BooleanVar(value=True)
        self.csv_format = tk.BooleanVar()
        self.max_file_size = tk.IntVar(value=10*1024*1024)
        self.encoding = tk.StringVar(value="utf-8")

        self.create_widgets()

    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Directory selection
        dir_frame = ttk.LabelFrame(main_frame, text="Directories to Scan", padding="5")
        dir_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.dir_listbox = tk.Listbox(dir_frame, height=4)
        self.dir_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E))

        dir_buttons_frame = ttk.Frame(dir_frame)
        dir_buttons_frame.grid(row=0, column=1, padx=(5, 0))

        ttk.Button(dir_buttons_frame, text="Add Directory", command=self.add_directory).grid(row=0, column=0, pady=(0, 5))
        ttk.Button(dir_buttons_frame, text="Remove Selected", command=self.remove_directory).grid(row=1, column=0)

        # Options frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Left column
        left_options = ttk.Frame(options_frame)
        left_options.grid(row=0, column=0, sticky=(tk.W, tk.N))

        ttk.Checkbutton(left_options, text="Case Insensitive", variable=self.case_insensitive).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(left_options, text="Whole Word", variable=self.whole_word).grid(row=1, column=0, sticky=tk.W)

        ttk.Label(left_options, text="Custom Patterns:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(left_options, textvariable=self.custom_patterns, width=40).grid(row=3, column=0, sticky=(tk.W, tk.E))

        # Right column
        right_options = ttk.Frame(options_frame)
        right_options.grid(row=0, column=1, sticky=(tk.W, tk.N), padx=(20, 0))

        ttk.Label(right_options, text="Max File Size (MB):").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(right_options, from_=1, to=100, textvariable=tk.IntVar(value=10)).grid(row=1, column=0, sticky=(tk.W, tk.E))

        ttk.Label(right_options, text="Encoding:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(right_options, textvariable=self.encoding).grid(row=3, column=0, sticky=(tk.W, tk.E))

        # Output frame
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(output_frame, textvariable=self.output_dir).grid(row=1, column=0, sticky=(tk.W, tk.E))
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=1, padx=(5, 0))

        format_frame = ttk.Frame(output_frame)
        format_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))

        ttk.Checkbutton(format_frame, text="JSON", variable=self.json_format).grid(row=0, column=0)
        ttk.Checkbutton(format_frame, text="CSV", variable=self.csv_format).grid(row=0, column=1, padx=(10, 0))

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))

        self.run_button = ttk.Button(button_frame, text="Run Scan", command=self.run_scan)
        self.run_button.grid(row=0, column=0, padx=(0, 10))

        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=1)

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, orient="horizontal", mode="indeterminate")
        self.progress.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        dir_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(0, weight=1)
        options_frame.columnconfigure(1, weight=1)
        output_frame.columnconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Setup logging to GUI
        self.setup_logging()

    def setup_logging(self):
        class GUITextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                self.text_widget.insert(tk.END, msg + '\n')
                self.text_widget.see(tk.END)

        handler = GUITextHandler(self.log_text)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.INFO)

    def add_directory(self):
        dir_path = filedialog.askdirectory(title="Select Directory to Scan")
        if dir_path and dir_path not in self.directories:
            self.directories.append(dir_path)
            self.update_dir_listbox()

    def remove_directory(self):
        selection = self.dir_listbox.curselection()
        if selection:
            index = selection[0]
            del self.directories[index]
            self.update_dir_listbox()

    def update_dir_listbox(self):
        self.dir_listbox.delete(0, tk.END)
        for dir_path in self.directories:
            self.dir_listbox.insert(tk.END, dir_path)

    def browse_output_dir(self):
        dir_path = filedialog.askdirectory(title="Select Output Directory")
        if dir_path:
            self.output_dir.set(dir_path)

    def run_scan(self):
        if not self.directories:
            messagebox.showerror("Error", "Please select at least one directory to scan.")
            return

        # Prepare scanner options
        patterns = None
        if self.custom_patterns.get().strip():
            patterns = [p.strip() for p in self.custom_patterns.get().split('\n') if p.strip()]

        formats = []
        if self.json_format.get():
            formats.append('json')
        if self.csv_format.get():
            formats.append('csv')

        if not formats:
            messagebox.showerror("Error", "Please select at least one output format.")
            return

        # Create scanner
        self.scanner = KeybindScanner(
            patterns=patterns,
            case_insensitive=self.case_insensitive.get(),
            whole_word=self.whole_word.get(),
            max_file_size=self.max_file_size.get(),
            encoding=self.encoding.get()
        )

        # Disable run button
        self.run_button.config(state='disabled')
        self.progress.start()

        # Run scan in thread
        self.scan_thread = threading.Thread(target=self._run_scan_thread, args=(formats,))
        self.scan_thread.start()

    def _run_scan_thread(self, formats):
        try:
            # Convert string paths to Path objects
            directories = [Path(d) for d in self.directories]

            # Run scan
            scan_data = self.scanner.scan_directories(directories)

            # Save results
            output_dir = Path(self.output_dir.get())
            self.scanner.save_results(scan_data, output_dir, formats)

            # Show summary
            self.root.after(0, lambda: self.show_results(scan_data))

        except Exception as e:
            logging.error(f"Scan failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scan failed: {e}"))
        finally:
            self.root.after(0, self.scan_complete)

    def show_results(self, scan_data):
        summary = f"Scan complete!\n\n"
        summary += f"Files scanned: {scan_data['total_files_scanned']}\n"
        summary += f"Matches found: {scan_data['total_matches']}\n"
        summary += f"Unique keybinds: {len(scan_data['aggregated'])}\n\n"

        if scan_data['aggregated']:
            summary += "Keybinds found:\n"
            for keybind in sorted(scan_data['aggregated'].keys()):
                count = len(scan_data['aggregated'][keybind])
                summary += f"  {keybind}: {count} occurrence{'s' if count != 1 else ''}\n"

        messagebox.showinfo("Scan Results", summary)

    def scan_complete(self):
        self.run_button.config(state='normal')
        self.progress.stop()

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)


def main():
    root = tk.Tk()
    app = KeybindScannerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()