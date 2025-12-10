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

        # Settings file
        self.settings_file = Path(__file__).parent / "settings.json"

        # Scanner instance
        self.scanner = None
        self.scan_thread = None
        self.scan_data = None

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

        # Load settings
        self.load_settings()

        self.create_widgets()

        # Update UI with loaded settings
        self.update_dir_listbox()

        # Save settings on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_settings(self):
        """Load settings from file."""
        try:
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Apply settings
                self.directories = settings.get('directories', [])
                self.output_dir.set(settings.get('output_dir', 'output'))
                self.custom_patterns.set(settings.get('custom_patterns', ''))
                self.case_insensitive.set(settings.get('case_insensitive', False))
                self.whole_word.set(settings.get('whole_word', False))
                self.json_format.set(settings.get('json_format', True))
                self.csv_format.set(settings.get('csv_format', False))
                self.max_file_size.set(settings.get('max_file_size', 10*1024*1024))
                self.encoding.set(settings.get('encoding', 'utf-8'))
                
                # Window geometry
                geometry = settings.get('geometry')
                if geometry:
                    self.root.geometry(geometry)
        except Exception as e:
            logging.warning(f"Failed to load settings: {e}")

    def save_settings(self):
        """Save current settings to file."""
        try:
            settings = {
                'directories': self.directories,
                'output_dir': self.output_dir.get(),
                'custom_patterns': self.custom_patterns.get(),
                'case_insensitive': self.case_insensitive.get(),
                'whole_word': self.whole_word.get(),
                'json_format': self.json_format.get(),
                'csv_format': self.csv_format.get(),
                'max_file_size': self.max_file_size.get(),
                'encoding': self.encoding.get(),
                'geometry': self.root.geometry()
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.warning(f"Failed to save settings: {e}")

    def on_close(self):
        """Handle window close event."""
        self.save_settings()
        self.root.destroy()

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
        ttk.Spinbox(right_options, from_=1, to=100, textvariable=self.max_file_size).grid(row=1, column=0, sticky=(tk.W, tk.E))

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

        self.view_button = ttk.Button(button_frame, text="View Keybindings", command=self.view_keybindings, state='disabled')
        self.view_button.grid(row=0, column=1, padx=(0, 10))

        self.map_button = ttk.Button(button_frame, text="View Binding Map", command=self.view_binding_map, state='disabled')
        self.map_button.grid(row=0, column=2, padx=(0, 10))

        ttk.Button(button_frame, text="Clear Log", command=self.clear_log).grid(row=0, column=3)

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
            max_file_size=self.max_file_size.get() * 1024 * 1024,
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
        self.scan_data = scan_data  # Store for viewing
        
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
        
        # Save settings after successful scan
        self.save_settings()

    def scan_complete(self):
        self.run_button.config(state='normal')
        self.progress.stop()
        
        # Enable view buttons if we have scan data
        if self.scan_data:
            self.view_button.config(state='normal')
            self.map_button.config(state='normal')

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def view_keybindings(self):
        """Open keybinding viewer window."""
        if not self.scan_data:
            messagebox.showerror("Error", "No scan data available. Please run a scan first.")
            return

        # Create viewer window
        viewer = tk.Toplevel(self.root)
        viewer.title("Keybinding Conflict Viewer")
        viewer.geometry("900x600")

        # Create treeview
        tree_frame = ttk.Frame(viewer, padding="10")
        tree_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Treeview with columns
        columns = ("Key", "Mod", "File", "Line", "Context")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        tree.heading("Key", text="Key")
        tree.heading("Mod", text="Mod Name")
        tree.heading("File", text="File")
        tree.heading("Line", text="Line")
        tree.heading("Context", text="Context")
        
        tree.column("Key", width=80, minwidth=60)
        tree.column("Mod", width=150, minwidth=100)
        tree.column("File", width=200, minwidth=150)
        tree.column("Line", width=60, minwidth=50)
        tree.column("Context", width=300, minwidth=200)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # Status label
        status_frame = ttk.Frame(viewer, padding="5")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        status_label = ttk.Label(status_frame, text="")
        status_label.grid(row=0, column=0, sticky=tk.W)

        # Populate treeview
        self.populate_keybinding_tree(tree, status_label)

        # Configure grid weights
        viewer.columnconfigure(0, weight=1)
        viewer.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        status_frame.columnconfigure(0, weight=1)

    def populate_keybinding_tree(self, tree, status_label):
        """Populate the treeview with keybinding data."""
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)

        if not self.scan_data or 'aggregated' not in self.scan_data:
            status_label.config(text="No keybinding data available")
            return

        aggregated = self.scan_data['aggregated']
        conflict_count = 0
        total_bindings = 0

        # Sort keys for consistent display
        for key in sorted(aggregated.keys()):
            bindings = aggregated[key]
            total_bindings += len(bindings)
            
            if len(bindings) > 1:
                conflict_count += 1
            
            # Insert parent item for the key
            parent_item = tree.insert("", tk.END, values=(key, f"{len(bindings)} mods", "", "", ""))
            
            # Color code conflicts
            if len(bindings) > 1:
                tree.item(parent_item, tags=("conflict",))
            
            # Insert child items for each binding
            for binding in bindings:
                mod_name = binding.get('mod_name', 'Unknown')
                file_path = binding['file_path']
                line_num = binding['line_number']
                context = binding['context'][:100]  # Truncate long contexts
                
                tree.insert(parent_item, tk.END, values=("", mod_name, file_path, line_num, context))

        # Configure tags for conflict highlighting
        tree.tag_configure("conflict", background="lightcoral")

        # Update status
        status_text = f"Total unique keys: {len(aggregated)} | Conflicts: {conflict_count} | Total bindings: {total_bindings}"
        status_label.config(text=status_text)

    def view_binding_map(self):
        """Open binding map visualization window."""
        if not self.scan_data:
            messagebox.showerror("Error", "No scan data available. Please run a scan first.")
            return

        # Create map window
        map_win = tk.Toplevel(self.root)
        map_win.title("Keybinding Relationship Map")
        map_win.geometry("1200x800")

        # Create canvas with scrollbars
        canvas_frame = ttk.Frame(map_win, padding="10")
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        canvas = tk.Canvas(canvas_frame, bg='white', 
                          xscrollcommand=h_scrollbar.set,
                          yscrollcommand=v_scrollbar.set,
                          scrollregion=(0, 0, 2000, 1500))
        
        h_scrollbar.config(command=canvas.xview)
        v_scrollbar.config(command=canvas.yview)

        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Control frame
        control_frame = ttk.Frame(map_win, padding="5")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))

        ttk.Label(control_frame, text="Zoom:").grid(row=0, column=0)
        zoom_var = tk.DoubleVar(value=1.0)
        zoom_scale = ttk.Scale(control_frame, from_=0.5, to=2.0, variable=zoom_var, 
                              command=lambda v: self.update_canvas_zoom(canvas, float(v)))
        zoom_scale.grid(row=0, column=1, padx=(5, 10))

        ttk.Button(control_frame, text="Reset View", command=lambda: self.reset_canvas_view(canvas)).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(control_frame, text="Save Image", command=lambda: self.save_canvas_image(canvas)).grid(row=0, column=3)

        # Configure grid weights
        map_win.columnconfigure(0, weight=1)
        map_win.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        control_frame.columnconfigure(4, weight=1)

        # Draw the binding map
        self.draw_binding_map(canvas, zoom_var.get())

    def draw_binding_map(self, canvas, zoom=1.0):
        """Draw the keybinding relationship map on canvas."""
        canvas.delete("all")  # Clear canvas
        
        if not self.scan_data or 'aggregated' not in self.scan_data:
            canvas.create_text(400, 300, text="No keybinding data available", font=("Arial", 16))
            return

        # Prepare data structures
        keys = list(self.scan_data['aggregated'].keys())
        mods = set()
        files = set()
        
        key_mods = {}  # key -> set of mods
        mod_files = {}  # mod -> set of files
        
        for key, bindings in self.scan_data['aggregated'].items():
            key_mods[key] = set()
            for binding in bindings:
                mod_name = binding.get('mod_name', 'Unknown')
                file_path = binding['file_path']
                mods.add(mod_name)
                files.add(file_path)
                key_mods[key].add(mod_name)
                if mod_name not in mod_files:
                    mod_files[mod_name] = set()
                mod_files[mod_name].add(file_path)

        # Convert to lists for positioning
        mods = sorted(list(mods))
        files = sorted(list(files))

        # Layout parameters
        margin = 50
        key_spacing = 120 * zoom
        mod_spacing = 100 * zoom
        file_spacing = 80 * zoom
        section_spacing = 300 * zoom

        # Position nodes
        key_positions = {}
        mod_positions = {}
        file_positions = {}

        # Keys on the left
        for i, key in enumerate(keys):
            x = margin
            y = margin + i * key_spacing
            key_positions[key] = (x, y)
            # Draw key node (circle)
            radius = 25 * zoom
            canvas.create_oval(x-radius, y-radius, x+radius, y+radius, 
                             fill='lightblue', outline='blue', width=2)
            canvas.create_text(x, y, text=key, font=("Arial", int(10*zoom), "bold"))

        # Mods in the middle
        mod_x = margin + section_spacing
        for i, mod in enumerate(mods):
            x = mod_x
            y = margin + i * mod_spacing
            mod_positions[mod] = (x, y)
            # Draw mod node (rectangle)
            width, height = 80 * zoom, 30 * zoom
            canvas.create_rectangle(x-width/2, y-height/2, x+width/2, y+height/2,
                                  fill='lightgreen', outline='green', width=2)
            # Truncate long mod names
            display_name = mod[:15] + "..." if len(mod) > 15 else mod
            canvas.create_text(x, y, text=display_name, font=("Arial", int(9*zoom)))

        # Files on the right
        file_x = mod_x + section_spacing
        for i, file in enumerate(files):
            x = file_x
            y = margin + i * file_spacing
            file_positions[file] = (x, y)
            # Draw file node (oval)
            width, height = 100 * zoom, 25 * zoom
            canvas.create_oval(x-width/2, y-height/2, x+width/2, y+height/2,
                             fill='lightyellow', outline='orange', width=2)
            # Truncate long file paths
            display_name = Path(file).name  # Just filename
            canvas.create_text(x, y, text=display_name, font=("Arial", int(8*zoom)))

        # Draw connections
        for key, key_mods_set in key_mods.items():
            key_x, key_y = key_positions[key]
            for mod in key_mods_set:
                if mod in mod_positions:
                    mod_x, mod_y = mod_positions[mod]
                    # Draw line from key to mod
                    color = 'red' if len(key_mods_set) > 1 else 'gray'
                    canvas.create_line(key_x + 25*zoom, key_y, mod_x - 40*zoom, mod_y,
                                     fill=color, width=2, arrow=tk.LAST)

        for mod, mod_files_set in mod_files.items():
            if mod in mod_positions:
                mod_x, mod_y = mod_positions[mod]
                for file in mod_files_set:
                    if file in file_positions:
                        file_x, file_y = file_positions[file]
                        # Draw line from mod to file
                        canvas.create_line(mod_x + 40*zoom, mod_y, file_x - 50*zoom, file_y,
                                         fill='purple', width=1, arrow=tk.LAST)

        # Update scroll region
        canvas.config(scrollregion=canvas.bbox("all"))

        # Add legend
        legend_x = margin
        legend_y = margin + len(keys) * key_spacing + 50
        canvas.create_text(legend_x, legend_y, text="Legend:", font=("Arial", int(12*zoom), "bold"), anchor=tk.W)
        canvas.create_oval(legend_x+5, legend_y+20, legend_x+25, legend_y+40, fill='lightblue', outline='blue')
        canvas.create_text(legend_x+35, legend_y+30, text="Keys", font=("Arial", int(10*zoom)), anchor=tk.W)
        canvas.create_rectangle(legend_x+5, legend_y+50, legend_x+65, legend_y+70, fill='lightgreen', outline='green')
        canvas.create_text(legend_x+75, legend_y+60, text="Mods", font=("Arial", int(10*zoom)), anchor=tk.W)
        canvas.create_oval(legend_x+5, legend_y+80, legend_x+85, legend_y+100, fill='lightyellow', outline='orange')
        canvas.create_text(legend_x+95, legend_y+90, text="Files", font=("Arial", int(10*zoom)), anchor=tk.W)
        canvas.create_line(legend_x+5, legend_y+115, legend_x+45, legend_y+115, fill='gray', width=2, arrow=tk.LAST)
        canvas.create_text(legend_x+55, legend_y+115, text="Single mod binding", font=("Arial", int(10*zoom)), anchor=tk.W)
        canvas.create_line(legend_x+5, legend_y+135, legend_x+45, legend_y+135, fill='red', width=2, arrow=tk.LAST)
        canvas.create_text(legend_x+55, legend_y+135, text="Conflict binding", font=("Arial", int(10*zoom)), anchor=tk.W)

    def update_canvas_zoom(self, canvas, zoom):
        """Update canvas zoom level."""
        self.draw_binding_map(canvas, zoom)

    def reset_canvas_view(self, canvas):
        """Reset canvas view to top-left."""
        canvas.xview_moveto(0)
        canvas.yview_moveto(0)

    def save_canvas_image(self, canvas):
        """Save canvas as image (placeholder - would need PIL/Pillow)."""
        messagebox.showinfo("Save Image", "Image saving not implemented yet.\n"
                                         "Would require PIL/Pillow library for canvas to image conversion.")


def main():
    root = tk.Tk()
    app = KeybindScannerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()