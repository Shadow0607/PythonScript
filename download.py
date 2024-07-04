import json
import requests
import time

# 設置 Synology NAS 的相關資訊
NAS_IP = '192.168.68.103'
NAS_USERNAME = 'all611'
NAS_PASSWORD = 'Wayne8467'
NAS_PATH ='/volume1/video/other'

class DownloadStation:
    def __init__(self, ip, port, username, password):
        self.base_url = f"http://{ip}:{port}/webapi"
        self.username = username
        self.password = password
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
        
            print(f"完整回應：{response_json}")
        
            if "data" in response_json and "sid" in response_json["data"]:
                self.sid = response_json["data"]["sid"]
                print("登錄成功")
            else:
                error_code = response_json.get("error", {}).get("code", "未知錯誤")
                print(f"登錄失敗。錯誤代碼：{error_code}")
                raise Exception(f"登錄失敗：{response_json}")
        except requests.RequestException as e:
            print(f"請求錯誤：{e}")
            raise Exception(f"網絡請求失敗：{e}")

    def add_torrent_task(self, torrent_url):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "create",
            "uri": torrent_url,
            "_sid": self.sid
        }
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


    def edit_task(self, task_id, destination=None):
        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "edit",
            "id": task_id,
            "_sid": self.sid
        }
        if destination:
            data["destination"] = destination
        response = requests.get(url, params=data)
        return response.json()
    
    def set_file_priority(self, task_id, files, min_size, max_size):
        file_priorities = []
        for idx, file in enumerate(files):
            file_size = int(file.get("size", 0))
            if min_size <= file_size <= max_size:
                file_priorities.append({"index": idx, "priority": "normal"})
            else:
                file_priorities.append({"index": idx, "priority": "skip"})

        url = f"{self.base_url}/DownloadStation/task.cgi"
        data = {
            "api": "SYNO.DownloadStation.Task",
            "version": "1",
            "method": "edit",
            "id": task_id,
            "file_priority": json.dumps(file_priorities),
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

def download_specific_files(ds, torrent_url, min_size, max_size, max_wait_time=1800):
    print(f"开始处理 torrent: {torrent_url}")
    print(f"文件大小范围: {min_size} - {max_size} bytes")

    # 添加 torrent 任务
    result = ds.add_torrent_task(torrent_url)
    if not result.get("success"):
        print(f"添加任务失败。错误信息: {result.get('error', '未知错误')}")
        return

    # 获取所有任务以找到新添加的任务
    all_tasks = ds.get_task_list()
    matching_tasks = [
        task for task in all_tasks.get("data", {}).get("tasks", [])
        if task.get("additional", {}).get("detail", {}).get("uri") == torrent_url
    ]

    if not matching_tasks:
        print("无法找到匹配的新任务")
        return

    task = matching_tasks[0]
    task_id = task.get("id")
    print(f"找到匹配的任务，ID: {task_id}")

    # 等待任务准备就绪并获取文件列表
    start_time = time.time()
    while time.time() - start_time < max_wait_time:
        task_info = ds.get_task_info(task_id)
        if task_info.get("success"):
            task = task_info.get("data", {}).get("tasks", [{}])[0]
            status = task.get("status")
            files = task.get("additional", {}).get("file", [])

            if status == "error":
                print(f"任务 {task_id} 出错")
                return
            elif status in ["downloading", "waiting", "paused"] and files:
                print(f"任务 {task_id} 已就绪，状态: {status}")
                break

        print(f"任务 {task_id} 尚未就绪或文件列表为空，等待 60 秒...")
        time.sleep(60)
    else:
        print(f"等待任务 {task_id} 就绪或获取文件列表超时")
        return

    # 设置文件优先级
    if files:
        print(f"找到 {len(files)} 个文件，正在设置优先级...")
        result = ds.set_file_priority(task_id, files, min_size, max_size)
        if result.get("success"):
            print("成功设置文件优先级")
        else:
            print(f"设置文件优先级失败。错误：{result.get('error', '未知错误')}")

        # 显示符合大小要求的文件
        selected_files = [file for file in files if min_size <= int(file.get("size", 0)) <= max_size]
        if selected_files:
            print(f"找到 {len(selected_files)} 个符合大小要求的文件:")
            for file in selected_files:
                print(f"名称: {file.get('filename')}, 大小: {file.get('size')} bytes")
        else:
            print(f"没有找到符合大小要求的文件。最小大小: {min_size} bytes, 最大大小: {max_size} bytes")
            print("正在删除任务...")
            delete_result = ds.delete_task(task_id)
            if delete_result.get("success"):
                print("成功删除任务")
            else:
                error_code = delete_result.get("error", {}).get("code")
                print(f"删除任务失败。错误代码: {error_code}")
    else:
        print("无法获取文件列表")

    print("下载任务设置完成")


# 使用示例
ds = DownloadStation(NAS_IP, 5000, NAS_USERNAME, NAS_PASSWORD)
ds.login()
# 在 download_specific_files 函數中使用

torrent_url = "magnet:?xt=urn:btih:7e417665febf4e049ae5a402c3404c24971300ac"
min_size = 100 * 1024 * 1024  # 100 MB
max_size = 10 * 1024 * 1024 * 1024  # 1 GB
download_specific_files(ds, torrent_url, min_size, max_size)

task_list = ds.get_task_list()
print(f"所有任務列表: {json.dumps(task_list, indent=2)}")