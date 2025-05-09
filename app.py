import customtkinter as ctk
from operations import *
from interface import *


# MAIN APPLICATION
root = ctk.CTk()
root.title("anam-IO")
root.geometry("900x400")


# INSTANTIATE MENU
menu = Menu(root, check_file=check_file, scan_directories=scan_directories, scan_directory=scan_directory)


# FORMATTING
container = ctk.CTkFrame(master=root)
container.pack(side="top", fill="both", expand=True, padx=5, pady=5)
container.grid_rowconfigure(0, weight=1)
for c in (0,1,2):
    container.grid_columnconfigure(c, weight=1)


# INSTANTIATE METADATA FILELIST AND WATCHER 
metadata = Metadata(container)
file_list = FileList(container, on_select=metadata.display_status)
watcher = FolderWatcher(config, file_list)


# ADD WATCHER, METADATA AND FILE LIST TO MENU AFTER THEY ARE INITIATED SINCE MOST OF THE MENU NEEDS TO BE INITIATED FIRST
menu.add_watcher(watcher)
menu.add_file_list(file_list=file_list)
menu.add_metadata(metadata)


# WATCH CONFIG
watch_config(file_list, menu, metadata)


# STARTUP SEQ
def startup_seq():
    menu.sentry_on()


# RUN
startup_seq()
root.mainloop()
