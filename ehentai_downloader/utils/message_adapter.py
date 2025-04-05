import os
import re
import yaml
import aiohttp
import asyncio
import glob
import logging
from pathlib import Path
from natsort import natsorted
from asyncio import Queue


class FileUploader:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.platform_type = self.config["platform"]["type"]
        self.http_host = self.config["platform"]["http_host"]
        self.http_port = self.config["platform"]["http_port"]
        self.api_token = self.config["platform"]["api_token"]

    def _load_config(self, config_path):
        """加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as file:
            return yaml.safe_load(file)

    def get_headers(self):
        """生成请求头，根据是否有API令牌添加授权信息"""
        headers = {'Content-Type': 'application/json'}
        if self.api_token:
            headers['Authorization'] = f'Bearer {self.api_token}'
        return headers

    async def get_group_root_files(self, group_id):
        """获取群文件根目录列表"""
        url = f"http://{self.http_host}:{self.http_port}/get_group_root_files"
        payload = {"group_id": group_id}
        headers = self.get_headers()

        print("发送给消息平台->" + str(payload))
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise Exception(
                        f"获取群文件根目录失败，状态码: {response.status}, 错误信息: {await response.text()}")
                res = await response.json()
                if res["status"] != "ok":
                    raise Exception(f"获取群文件根目录失败，状态码: {res['status']}\n完整消息: {str(res)}")
                return res["data"]

    async def create_group_file_folder(self, group_id, folder_name):
        """创建群文件夹"""
        url = f"http://{self.http_host}:{self.http_port}/create_group_file_folder"

        # 根据平台类型准备不同的请求参数
        if self.platform_type == 'napcat':
            payload = {
                "group_id": group_id,
                "folder_name": folder_name
            }
        elif self.platform_type == 'llonebot':
            payload = {
                "group_id": group_id,
                "name": folder_name
            }
        elif self.platform_type == 'lagrange':
            payload = {
                "group_id": group_id,
                "name": folder_name,
                "parent_id": "/"
            }
        else:
            raise Exception("消息平台配置有误, 只能是'napcat', 'llonebot'或'lagrange'")

        headers = self.get_headers()
        print("发送给消息平台->" + str(payload))

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"创建群文件夹失败，状态码: {response.status}, 错误信息: {await response.text()}")
                res = await response.json()
                print("消息平台返回->" + str(res))
                if res["status"] != "ok":
                    raise Exception(f"创建群文件夹失败，状态码: {res['status']}\n完整消息: {str(res)}")
                try:
                    return res["data"]["folder_id"]
                except Exception:
                    return None

    async def get_group_folder_id(self, group_id, folder_name: str = '/'):
        """获取(或创建)群文件夹ID"""
        if folder_name == '/':
            return '/'

        # 尝试查找文件夹
        data = await self.get_group_root_files(group_id)
        for folder in data.get('folders', []):
            if folder.get('folder_name') == folder_name:
                return folder.get('folder_id')

        # 如果未找到，创建文件夹
        folder_id = await self.create_group_file_folder(group_id, folder_name)
        if folder_id is None:
            # 再次检查，以防文件夹已创建但未返回ID
            data = await self.get_group_root_files(group_id)
            for folder in data.get('folders', []):
                if folder.get('folder_name') == folder_name:
                    return folder.get('folder_id')
            return "/"
        return folder_id

    async def upload_file(self, ctx, path, name, folder_name='/'):
        """上传文件"""
        all_files = os.listdir(path)
        pattern = re.compile(rf"^{re.escape(name)}(?: part \d+)?\.pdf$")
        matching_files = [
            os.path.join(path, f) for f in all_files if pattern.match(f)
        ]
        files = natsorted(matching_files)
    
        if not files:
            raise FileNotFoundError("未找到符合命名的文件")
    
        is_private = ctx.event.launcher_type == "person"
        target_id = ctx.event.sender_id if is_private else ctx.event.launcher_id
        url_type = "upload_private_file" if is_private else "upload_group_file"
        url = f"http://{self.http_host}:{self.http_port}/{url_type}"
    
        base_payload = {
            "file": None,
            "name": None,
            "user_id" if is_private else "group_id": target_id
        }
    
        if not is_private:
            base_payload["folder_id"] = await self.get_group_folder_id(target_id, folder_name)
    
        queue = Queue()
        
        async def worker():
            async with aiohttp.ClientSession() as session:
                while not queue.empty():
                    file = await queue.get()
                    payload = base_payload.copy()
                    payload.update({
                        "file": file,
                        "name": os.path.basename(file)
                    })
                
                result = await self._upload_single_file(session, url, self.get_headers(), payload)
                results.append(result)
                queue.task_done()
    
        for file in files:
            await queue.put(file)
    
        results = []
        workers = [worker() for _ in range(1)]
        await asyncio.gather(*workers)
    
        return self._process_results(results)

    async def _upload_single_file(self, session, url, headers, payload):
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                response.raise_for_status()
                res = await response.json()

                if res["status"] != "ok":
                    return {"success": False, "error": res.get("message")}

                return {"success": True, "data": res.get("data")}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _process_results(self, results):
        successes = [r["data"] for r in results if r["success"]]
        errors = [r["error"] for r in results if not r["success"]]

        if errors:
            logging.warning(f"部分文件上传失败: {errors}")

        return {
            "total": len(results),
            "success_count": len(successes),
            "failed_count": len(errors),
            "details": {
                "successes": successes,
                "errors": errors
            }
        }
