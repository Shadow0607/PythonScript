# !/usr/bin/python
# coding:utf-8
#!/usr/bin/env python3

import os
import re
import shutil
import time
import datetime

VIDEO_DIR = "/volume1/video"

TO_REPLACE = [
    r"@jnty60\\.app", "@69館", r"@69av\\.me", r"aavv39\\.xyz@","@九游@jy",r"@九游@5jy.cc",
    "@jnty4588.com_", "@九游@  jy", "5jy.cc-", "@江南-", "hhd800.com@", 
    "aavv38.xyz@435", "[gg5.co]", "@江南@", "jnty4588.com", "nyap2p.com",
    "aavv38.xyz@","jn-89-9.vip","-2K","-4K","-6K","@江南@jnty4588.com","@九游娛樂@ 5jy.cc",
    "aavv-3-8.xyz@","@九游@","mp-4","kfa11.com@"
]

#record_time =86400
record_time =300

DELETE_FILENAME =["社區最新情報","台妹子"]
file_extensions = [".mp4", ".srt", ".wmv",".jpg"]
mp4_files = []
# 紀錄變動文件名稱的檔案
def log(message):
    # 获取当前日期
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    # 构建日志文件名
    log_file = f"/volume1/homes/all611/Python/log_folder/log_{today}.txt"
    log_folder = "/volume1/homes/all611/Python/log_folder"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder)
    # 检查日志文件是否存在，如果不存在则创建
    if not os.path.exists(log_file):
        with open(log_file, "w") as f:
            pass
    # 写入日志
    with open(log_file, "a") as f:
        log_entry = f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n"
        f.write(log_entry)

def get_files_modified_within_last_day(dir_path):
    current_time = time.time()
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            if any(file.lower().endswith(ext) for ext in file_extensions) and (current_time - os.path.getmtime(file_path)) < record_time:
                yield file_path

def get_download_list():
    for parent_dir in os.listdir(VIDEO_DIR):
        parent_path = os.path.join(VIDEO_DIR, parent_dir)
        if os.path.isdir(parent_path):
            # 获取当前目录下的所有 MP4 文件，并按字母顺序排序
            mp4_files = sorted([filename for filename in os.listdir(parent_path) if filename.lower().endswith(".mp4")])
            # 自定义排序规则：按照文件名的字母顺序，然后按照文件名中的数字大小进行排序
            mp4_files.sort(key=lambda x: (x.split('-')[0], int(''.join(filter(str.isdigit, x)))))
            # 遍历排序后的文件列表
            for filename in mp4_files:
                base_name = os.path.splitext(filename)[0]
                jpg_filename = f"{base_name}.jpg"
                jpg_path = os.path.join(parent_path, jpg_filename)
                mp4_path = os.path.join(parent_path, filename)
                if os.path.exists(jpg_path):
                    return True
                else:
                    return False

'''def rename_files():
    for file_path in get_files_modified_within_last_day(VIDEO_DIR):
        print(file_path)
        for pattern in DELETE_FILENAME:
            if contains_keyword(file_path, pattern):
                print(f"Removing file: {file_path}")  # For debugging purposes
                os.remove(file_path)
        directory, filename = os.path.split(file_path)
        new_filename = clean_filename(filename)
        new_file_path = os.path.join(directory, new_filename)
        if new_file_path != file_path:  # 如果文件名确实有变化
            log(f"重命名文件: {file_path} -> {new_file_path}")
            shutil.move(file_path, new_file_path)'''

def rename_files():
    for file_path in get_files_modified_within_last_day(VIDEO_DIR):
        # 检查是否存在相同文件名但不同扩展名的 ".mp4" 和 ".jpg" 文件
        if get_download_list():
            continue  # 如果存在，则跳过当前文件，不执行重命名操作
        
        print(file_path)
        for pattern in DELETE_FILENAME:
            if contains_keyword(file_path, pattern):
                print(f"Removing file: {file_path}")  # For debugging purposes
                os.remove(file_path)
        directory, filename = os.path.split(file_path)
        new_filename = clean_filename(filename)
        new_file_path = os.path.join(directory, new_filename)
        if new_file_path != file_path:  # 如果文件名确实有变化
            log(f"重命名文件: {file_path} -> {new_file_path}")
            shutil.move(file_path, new_file_path)

def is_valid_filename(filename):
    extensions_pattern = '|'.join([re.escape(ext) for ext in file_extensions])
    # 正则表达式模式，用于匹配期望的文件名格式
    #pattern = r'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?\.mp4$'
    pattern = rf'^[a-zA-Z]+-\d+(-[a-zA-Z]+)?({extensions_pattern})$'
    # 如果文件名符合模式，则返回 True，否则返回 False
    return bool(re.match(pattern, filename, re.IGNORECASE))

def clean_parts(parts):
    # 检查末尾两个元素合并后是否为 'mp4' 或 'MP4'
    if len(parts) >= 2 and (parts[-2] + parts[-1]).lower() == 'mp4':
        parts = parts[:-2]  # 移除末尾两个元素
    return parts

def clean_filename(filename):
    name, ext = os.path.splitext(filename)  # 将文件名和扩展名分开
    for pattern in TO_REPLACE:
        if contains_keyword(name, pattern):
            log(f"The name '{name}' contains the keyword '{pattern}'.")
            name = name.replace(pattern, '')  # 需要将替换后的结果重新赋值给 name
            name = name.replace('_', '-')
            name = name.strip()
    name = re.findall(r'[a-zA-Z]+|\d+|[a-zA-Z]+', name)
    if len(name) > 2:
        last_element = name[-1].lower()
        if last_element in ['ch', 'ucmp4', 'chnyap2p.com', 'uc', 'mp4']:
            name[-1] = 'C'
        elif last_element in ['uncensored', 'ump4']:
            name[-1] = 'U'

    name = '-'.join(name)
    # 去掉可能的多余空格
    name = name.strip()
    name_parts = re.findall(r'[a-zA-Z]+|\d+', name)
    name_parts = clean_parts(name_parts)
    new_name = '-'.join(name_parts)
    
    for pattern in TO_REPLACE:
        if contains_keyword(new_name, pattern):
            log(f"The name '{new_name}' contains the keyword '{pattern}'.")
            new_name = new_name.replace(pattern, '')  # 需要将替换后的结果重新赋值给 name
            new_name = new_name.strip()
    new_filename = new_name.upper() + ext
    log(new_filename)
    if not is_valid_filename(new_filename):
        log(f"Error: The filename '{new_filename}' does not match the expected pattern.")
        return filename
    
    return new_filename

def contains_keyword(name, keyword):
    return keyword in name

def move_and_rename_files():
    global mp4_files  # 将 mp4_files 声明为全局变量
    modified_files = []
    oldfolder_array =[]
    rename_files()
    for file_path in get_files_modified_within_last_day(VIDEO_DIR):
        log(f"檔案名稱1:{file_path}\n")
        mp4_files.append(file_path)
    log("原始值：\n" + "\n".join(mp4_files))
    for file_path in mp4_files:
        log(f"{file_path}長度：\n"+str(len(file_path.split("/"))))
    mp4_files = [file_path for file_path in mp4_files if len(file_path.split("/")) >= 6]
    log("修改後的原始值："+ "\n".join(mp4_files))
    for file_path in mp4_files:
        components = file_path.split("/")
        new_file_path = "/".join(components[:4] + components[-1:])
        oldfolder= "/".join(components[:4]+ components[-2:-1])
        oldfolder_array.append(oldfolder)
        modified_files.append(new_file_path)
    log("修改後的新陣列值："+ "\n".join(modified_files))
    
    for old_path, new_path in zip(mp4_files, modified_files,):
        log(f"將 {old_path} 移动到 {new_path}")
        shutil.move(old_path, new_path)
    
    print(oldfolder_array)
    
    for oldfolder in oldfolder_array:
        print(oldfolder)
        if os.path.exists(oldfolder):
            try:
                shutil.rmtree(oldfolder)
                log(f"將 {oldfolder} 刪除")
            except Exception as e:
                log(f"刪除 {oldfolder} 時發生錯誤: {e}")
        else:
            log(f"目錄 {oldfolder} 不存在，無法刪除")
    
    for root, dirs, files in os.walk(VIDEO_DIR, topdown=False):
        # 排除 @eaDir 目录
        dirs[:] = [d for d in dirs if d != "@eaDir"]
        for name in dirs:
            dir_path = os.path.join(root, name)
            # 检查文件夹是否仅包含 @eaDir 或为空
            if not os.listdir(dir_path) or os.listdir(dir_path) == ["@eaDir"]:
                log(f"删除空文件夹或仅包含 @eaDir 的文件夹: {dir_path}")
                try:
                    shutil.rmtree(dir_path)
                    log(f"刪除文件夾: {dir_path}")
                except Exception as e:
                    log(f"刪除 {dir_path} 時發生錯誤: {e}")
        
if __name__ == "__main__":
    move_and_rename_files()
