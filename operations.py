import json
import os
import subprocess
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import platform

config = None

# LOAD CONFIG
def load_config():
    global config
    with open('config.json', 'r') as file:
        config = json.load(file)

load_config()

# RUN EACH CHECK ON A GIVEN FILE
def check_file(file):
    checks = config["checks"]
    variable_substring = config["command_variable_substring"]
    status = {
        "file": file,
        "anomaly": False,
        "command_results": []
    }
    for check in checks:
        command = check["command"].replace(variable_substring, f'"{file}"')
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        output = ",".join(output.split())
        target = check["target"]
        name = check["name"]
        match = True
        if output != target:
            match = False
            status["anomaly"] = True
        status["command_results"].append({
            "name": name,
            "match": match,
            "target": target,
            "output": output
        })
    return status


# SCAN A DIRECTORY
def scan_directory(directory):
    files = []
    file_types = config["scan_file_types"]
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.startswith("._"):
                continue
            if f.lower().endswith(tuple(file_types)):
                full_path = os.path.join(root, f)
                if os.path.isfile(full_path):
                    files.append(full_path)
    return files



# SCAN ALL DIRECTORIES IN THE CONFIG
def scan_directories():
    files = []
    directories = config["scan_directories"]
    for path in directories:
        files = files + scan_directory(path)

    return files


# MAKES SURE A FILE ISN'T MID COPY
def wait_until_stable(path, seconds=2, interval=0.5):
    last_size    = -1
    stable_since = None                     # when size first stopped changing

    while True:
        try:
            size = os.path.getsize(path)
        except FileNotFoundError:           # copy aborted / file vanished
            return False

        locked = False                      # try a no‑op rename as a lock test
        try:
            os.rename(path, path)           # raises PermissionError if writer still holds the file
        except (PermissionError, OSError):
            locked = True

        if size == last_size and not locked:
            if stable_since is None:
                stable_since = time.monotonic()
            elif time.monotonic() - stable_since >= seconds:
                return True                 # size steady & not locked
        else:                               # size changed or file still locked
            last_size    = size
            stable_since = None

        time.sleep(interval)

# WATCHER 
class FolderWatcher:
    
    def __init__(self, config, filelist):
        self.config      = config        
        self.filelist    = filelist      
        self._stop_event = threading.Event()
        self._thread     = None

    def process_after_copy(self, path):
        if wait_until_stable(path):
            status = check_file(path)
            self.filelist.add_file(status)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self.watcher_loop, daemon=True)
        self._thread.start()

    def stop(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join()

    def watcher_loop(self):
        file_types = self.config["scan_file_types"]

        class ContentChangeHandler(FileSystemEventHandler):
            def on_created(self, event):
                if event.is_directory: return
                if not event.src_path.lower().endswith(tuple(file_types)): return
                threading.Thread(
                    target=self_outer.process_after_copy,
                    args=(event.src_path,),
                    daemon=True
                ).start()

            def on_deleted(self, event):
                if event.is_directory:
                    return
                file_name = os.path.basename(event.src_path)
                if (not file_name.startswith('.')
                        and file_name.lower().endswith(tuple(file_types))):
                    self_outer.filelist.remove_file(event.src_path)

        self_outer = self 
        observer   = Observer()
        for path in self.config["scan_directories"]:
            observer.schedule(ContentChangeHandler(), path=path, recursive=True)
        observer.start()

        try:
            while not self._stop_event.is_set():
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()


# WATCH CONFIG FOR MODIFICATIONS
def watch_config(file_list, menu, metadata):
    cfg = Path(__file__).resolve().parent / "config.json"
    class _Handler(FileSystemEventHandler):
        def on_modified(self, event):
            if not event.is_directory and Path(event.src_path) == cfg:
                load_config()
                menu.sentry_on()
    observer = Observer()
    observer.schedule(_Handler(), path=cfg.parent, recursive=False)
    observer.start()
    def _keep_alive():
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    threading.Thread(target=_keep_alive, daemon=True).start()

