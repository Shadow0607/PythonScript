#!/usr/bin/env python3
# coding:utf-8

import os
import shutil
import time
from typing import Generator
from config_reader import load_NAS_config, load_log_config
from logger import log
from database_manager import DatabaseManager
from utils import process_filename, clean_filename, FILE_EXTENSIONS, VIDEO_DIR

config = load_NAS_config()
config_log = load_log_config()
db_manager = DatabaseManager()

RECORD_TIME = 3600 * 10  # 10 hours

def logger_message(message):
    log(message, config_log['LOG_FOLDER'], 'move_file')

def get_recent_files(dir_path: str) -> Generator[str, None, None]:
    current_time = time.time()
    for root, _, files in os.walk(dir_path):
        if "@eaDir" in root:
            continue
        for file in files:
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue
            file_path = os.path.join(root, file)
            if (any(file.lower().endswith(ext) for ext in FILE_EXTENSIONS) and
                (current_time - os.path.getmtime(file_path)) < RECORD_TIME):
                yield file_path

def process_files():
    rename_files()
    move_files()
    delete_unnecessary_files_and_folders(VIDEO_DIR)
    clean_empty_folders(VIDEO_DIR)

def rename_files():
    for file_path in get_recent_files(VIDEO_DIR):
        directory, filename = os.path.split(file_path)
        video_num, category, is_valid = process_filename(filename)
        if not is_valid:
            logger_message(f"Invalid filename: {filename}")
            continue
        
        path, new_filename = clean_filename(filename)
        if path is None:
            new_file_path = os.path.join(directory, new_filename)
        else:
            new_file_path = os.path.join(path, new_filename)
        
        if new_file_path != file_path:
            try:
                print(f"Renaming file: {file_path} -> {new_file_path}")
                shutil.move(file_path, new_file_path)
            except Exception as e:
                logger_message(f"Error renaming file {file_path}: {e}")

def move_files() -> None:
    files_to_move = [f for f in get_recent_files(VIDEO_DIR)]
    for file_path in files_to_move:
        components = file_path.split("/")
        video_num, category, is_valid = process_filename(components[-1])
        if not is_valid:
            logger_message(f"Invalid filename: {components[-1]}")
            continue
        
        path = db_manager.get_path_video_num(video_num)
        if path is None:
            new_file_path = os.path.join(file_path, components[-1])
        else:
            new_file_path = os.path.join(path, components[-1])
                
        print(f"Moving {file_path} to {new_file_path}")
        shutil.move(file_path, new_file_path)        

def delete_unnecessary_files_and_folders(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        if "@eaDir" in root:
            continue

        for file in files:
            if file == "SYNOVIDEO_VIDEO_SCREENSHOT.jpg":
                continue

            file_path = os.path.join(root, file)
            video_num, _, is_valid = process_filename(file)
            
            if not is_valid or db_manager.check_video_num(video_num) is None:
                try:
                    os.remove(file_path)
                    print(f"Deleted file: {file_path}")
                    logger_message(f"Deleted file: {file_path}")
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
                    logger_message(f"Error deleting file {file_path}: {e}")

        if not any(files) and not any(dirs):
            try:
                shutil.rmtree(root)
                logger_message(f"Deleted empty folder: {root}")
            except Exception as e:
                logger_message(f"Error deleting folder {root}: {e}")

def clean_empty_folders(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            
            if os.listdir(dir_path) == ["@eaDir"]:
                try:
                    shutil.rmtree(os.path.join(dir_path, "@eaDir"))
                    os.rmdir(dir_path)
                    logger_message(f"Deleted folder with only @eaDir: {dir_path}")
                    print(f"Deleted folder with only @eaDir: {dir_path}")
                except Exception as e:
                    logger_message(f"Error deleting folder {dir_path}: {e}")
            
            elif not os.listdir(dir_path):
                try:
                    logger_message(f"Deleted empty folder: {dir_path}")
                    print(f"Deleted empty folder: {dir_path}")
                except Exception as e:
                    print(f"Error deleting empty folder {dir_path}: {e}")

if __name__ == "__main__":
    process_files()