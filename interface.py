import customtkinter as ctk
from operations import *
from notifypy import Notify
from pathlib import Path

# LEFT SCROLLABLE FRAME OF FILE NAMES
class FileList:
    def __init__(self, parent, on_select):
        self.on_select = on_select
        self.frame = ctk.CTkScrollableFrame(master=parent)
        self.frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        self.frame.grid_columnconfigure(0, weight=1)
        self.row_count = 0
        self.buttons = []

    def namer(self, text):
        name = text
        if len(text) >= 48:
            name = f"...{name[-45:]}"
        return name
    
    def add_file(self, status):
        self.row_count += 1
        file_name = status["file"]
        display_text = self.namer(file_name)
        color = "DarkGreen"
        if status["anomaly"]:
            color = "DarkRed"

            # Note: notify logic should probably not live here but idk where to put it yet
            notification = Notify()
            notification.title = "Anomaly Detected"
            notification.message = f"{display_text}"
            notification.send()

        btn = ctk.CTkButton(
            master=self.frame,
            text=display_text,
            cursor="hand2",
            fg_color=color,
            hover_color=color,
            anchor="w",
            command=lambda i=status: self.on_select(i)
        )
        btn._text_label.grid_configure(sticky="w", padx=(5, 0))
        btn.grid(row=self.row_count, column=0, sticky="ew", padx=2, pady=2)
        self.buttons.append(btn)

    def clear(self):
        self.row_count = 0
        for btn in self.buttons:
            btn.destroy()

    def remove_file(self, file_name):
        for btn in self.buttons:
            if btn.cget("text") == self.namer(file_name):
                btn.destroy()


# POPULATES THE RIGHT SCROLLABLE FRAME WITH METADATA
class Metadata:
    def __init__(self, parent):
        self.frame = ctk.CTkScrollableFrame(master=parent)
        self.frame.grid(row=0, column=1, columnspan=2, sticky="nsew", padx=2, pady=2)
        self.frame.grid_columnconfigure(0, weight=1)
        self.next_row = 0

    def clear(self):
        for child in self.frame.winfo_children():
            child.destroy()
        self.next_row = 0

    def display_filename(self, filename):
        for child in self.frame.winfo_children():
            child.destroy()
        ctk.CTkLabel(master=self.frame, text=filename, anchor="w").grid(row=0, column=0, sticky="w", padx=5, pady=(5,0))
        ctk.CTkLabel(master=self.frame, text="", anchor="w").grid(row=1, column=0, sticky="w", padx=5, pady=(0,5))
        self.next_row = 2

    def insert_section(self, name, target, observed, color):
        r = self.next_row
        lbl_kwargs = dict(master=self.frame, anchor="w", text_color=color)  
        ctk.CTkLabel(text=name,     **lbl_kwargs).grid(row=r,   column=0, sticky="w", padx=5, pady=(0,2))
        ctk.CTkLabel(text=f"Target: {target}",   **lbl_kwargs).grid(row=r+1, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(text=f"Observed: {observed}", **lbl_kwargs).grid(row=r+2, column=0, sticky="w", padx=5, pady=(2,0))
        ctk.CTkLabel(text="",       **lbl_kwargs).grid(row=r+3, column=0, sticky="w", padx=5, pady=(0,5))
        self.next_row += 4

    def display_status(self, status):
        self.display_filename(status["file"])
        for result in status["command_results"]:
            color = "white"
            if not result["match"]:
                color = "red"
            self.insert_section(
                name=result["name"],
                target=result["target"],
                observed=result["output"],
                color=color
            )


# TOP MENU BUTTONS
class Menu:
    def __init__(self, parent, check_file, scan_directories, scan_directory):
        f = ctk.CTkFrame(master=parent)
        f.pack(side="top", anchor="w", pady=5, padx=5)
        self.scan_file_btn = ctk.CTkButton(master=f, text="Scan File",  width=100, cursor="hand2", command=self.scan_file)
        self.scan_folder_btn = ctk.CTkButton(master=f, text="Scan Folder", width=100, cursor="hand2", command=self.scan_folder)
        self.sentry_btn = ctk.CTkButton(master=f, text="Sentry", width=100, cursor="hand2", command=self.toggle_sentry)
        self.edit_config_btn = ctk.CTkButton(master=f, text="Edit Config", width=100, cursor="hand2",command=self.edit_config)
        self.scan_file_btn.pack(side="left", padx=2)
        self.scan_folder_btn.pack(side="left", padx=2)
        self.sentry_btn.pack(side="left", padx=2)
        self.edit_config_btn.pack(side="left", padx=2)
        self.watcher = None
        self.check_file = check_file
        self.file_list = None
        self.scan_directories = scan_directories
        self.metadata = None
        self.scan_directory = scan_directory

    def add_watcher(self, watcher):
        self.watcher = watcher

    def add_file_list(self, file_list):
        self.file_list = file_list

    def add_metadata(self, metadata):
        self.metadata = metadata

    def sentry_on(self):
        self.metadata.clear()
        self.file_list.clear()
        self.sentry_btn.configure(text="Sentry On", fg_color="darkgoldenrod")
        files = scan_directories()
        for file in files:
            status = check_file(file)
            self.file_list.add_file(status)
        self.watcher.start()
        
    def sentry_off(self):
        self.sentry_btn.configure(text="Sentry On", fg_color="#1f6aa5")
        self.sentry_btn.configure(text="Sentry")
        self.watcher.stop()
        self.file_list.clear()

    def scan_file(self):
        file_path = ctk.filedialog.askopenfilename()
        if file_path:
            self.sentry_off()
            status = check_file(file_path)
            self.file_list.add_file(status)
            self.metadata.display_status(status)

    def scan_folder(self):
        self.metadata.clear()
        self.file_list.clear()
        folder = ctk.filedialog.askdirectory()
        if folder:
            self.sentry_off()
            files = scan_directory(folder)
            for file in files:
                status = check_file(file)
                self.file_list.add_file(status)

    def toggle_sentry(self):
        button_state = self.sentry_btn.cget("text")
        if button_state == "Sentry On":
            self.sentry_off()
        else:
            self.sentry_on()

    def edit_config(self):
        cfg = Path(__file__).resolve().parent / "config.json"
        sys = platform.system()
        if sys == "Windows":
            os.startfile(cfg)          
        elif sys == "Darwin":
            subprocess.run(["open", cfg])
        else:                         
            subprocess.run(["xdg-open", cfg])
