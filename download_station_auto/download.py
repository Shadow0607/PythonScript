import json
import requests
import time
from config_reader import load_NAS_config,load_log_config
from logger import log

config = load_NAS_config()
config_log =load_log_config()

def logger_message(message):
    log(message,config_log['LOG_FOLDER'], 'download')

class DownloadStation:
    def __init__(self):
        self.base_url = f"http://{config['NAS_IP']}:5000/webapi"
        self.username = config['NAS_USERNAME']
        self.password = config['NAS_PASSWORD']
        self.sid = None

    def login(self):
        url = f"{self.base_url}/auth.cgi"
        data = {
            "api": "SYNO.API.Auth",
            "version": "3",
            "method": "login",
            "account": self.username,
            "passwd": self.password,
            "session": "DownloadStation",
            "format": "json"
        }
        try:
            response = requests.get(url, params=data)
            response.raise_for_status()  # 如果 HTTP 錯誤發生，將會拋出異常
            response_json = response.json()
        
            logger_message(f"完整回應：{response_json}")
        
            if "data" in response_json and "sid" in response_json["data"]:
                self.sid = response_json["data"]["sid"]
                logger_message("登錄成功")
            else:
                error_code = response_json.get("error", {}).get("code", "未知錯誤")
                logger_message(f"登錄失敗。錯誤代碼：{error_code}")
                raise Exception(f"登錄失敗：{response_json}")
        except requests.RequestException as e:
            logger_message(f"請求錯誤：{e}")
            raise Exception(f"網絡請求失敗：{e}")

    def add_torrent_task(self, torrent_url, destination=None):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "create",
            "uri": torrent_url,
            "_sid": self.sid
        }
        if destination:
            data["destination"] = destination
        response = requests.get(url, params=data)
        return response.json()

    def get_task_info(self, task_id):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "getinfo",
            "id": task_id,
            "additional": "detail,file,transfer",  # 確保這裡包含 "file"
            "_sid": self.sid
        }
        response = requests.get(url, params=data)
        return response.json()
    
    def get_all_tasks(self):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "list",
            "_sid": self.sid
        }
        response = requests.get(url, params=data)
        return response.json()

    def get_task_list(self):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "list",
            "additional": "detail,file,transfer",
            "_sid": self.sid
        }
        response = requests.get(url, params=data)
        return response.json()
    def delete_task(self, task_id):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "delete",
            "id": task_id,
            "_sid": self.sid
        }
        response = requests.get(url, params=data)
        return response.json()
    
    def clear_completed_tasks(self):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "delete",
            "additional": "detail",
            "_sid": self.sid
        }
        
        # 獲取所有任務
        task_list = self.get_task_list()
        tasks_to_delete = []
        
        # 篩選出已完成和錯誤的任務
        for task in task_list.get("data", {}).get("tasks", []):
            if task.get("status") in ["finished", "error"]:
                tasks_to_delete.append(task.get("id"))
        
        if tasks_to_delete:
            # 如果有需要刪除的任務，則刪除它們
            data["id"] = ",".join(tasks_to_delete)
            response = requests.get(url, params=data)
            result = response.json()
            
            if result.get("success"):
                logger_message(f"成功清除 {len(tasks_to_delete)} 個已完成或錯誤的任務")
            else:
                logger_message(f"清除任務失敗。錯誤：{result.get('error', '未知錯誤')}")
        else:
            logger_message("沒有找到需要清除的已完成或錯誤任務")

        # 顯示剩餘的任務
        remaining_tasks = self.get_task_list()
        logger_message(f"剩餘任務數量：{len(remaining_tasks.get('data', {}).get('tasks', []))}")

    def logout(self):
        if self.sid:
            url = f"{self.base_url}/auth.cgi"
            data = {
                "api": "SYNO.API.Auth",
                "version": "1",
                "method": "logout",
                "session": "DownloadStation",
                "_sid": self.sid
            }
            try:
                response = requests.get(url, params=data)
                response.raise_for_status()
                response_json = response.json()
                
                if response_json.get("success"):
                    logger_message("成功登出")
                    self.sid = None
                else:
                    logger_message("登出失敗")
            except requests.RequestException as e:
                logger_message(f"登出時發生錯誤：{e}")

def download_specific_files(ds, torrent_url, min_size, max_size, destination, max_wait_time=1800):
    logger_message(f"开始处理 torrent: {torrent_url}")
    logger_message(f"文件大小范围: {min_size} - {max_size} bytes")
    logger_message(f"目标路径: {destination}")

    # 添加 torrent 任务
    result = ds.add_torrent_task(torrent_url)
    if not result.get("success"):
        logger_message(f"添加任务失败。错误信息: {result.get('error', '未知错误')}")
        return

    # 获取所有任务以找到新添加的任务
    all_tasks = ds.get_task_list()
    matching_tasks = [
        task for task in all_tasks.get("data", {}).get("tasks", [])
        if task.get("additional", {}).get("detail", {}).get("uri") == torrent_url
    ]

    if not matching_tasks:
        logger_message("无法找到匹配的新任务")
        return

    task = matching_tasks[0]
    task_id = task.get("id")
    logger_message(f"找到匹配的任务，ID: {task_id}")


    logger_message("下载任务设置完成")
    return
