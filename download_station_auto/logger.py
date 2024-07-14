import os
from datetime import datetime
import inspect

def get_script_name():
    stack = inspect.stack()
    caller_path = stack[1].filename
    return os.path.splitext(os.path.basename(caller_path))[0]

def log(message, log_folder, prefix=None):
    today = datetime.now().strftime("%Y-%m-%d")
    if prefix is None:
        prefix = get_script_name()
    
    log_file = os.path.join(log_folder, f"{prefix}_{today}.txt")
    
    os.makedirs(log_folder, exist_ok=True)
    
    with open(log_file, "a", encoding='utf-8') as f:
        log_entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        f.write(log_entry)