import yaml
import aiohttp
from pathlib import Path

config_path = Path(__file__).parent.parent.parent / "config.yaml"

with open(config_path, "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# 获取 platform 配置
platform_type = config["platform"]["type"]
http_host = config["platform"]["http_host"]
http_port = config["platform"]["http_port"]
api_token = config["platform"]["api_token"]


def get_headers():
    """生成请求头，根据是否有API令牌添加授权信息"""
    headers = {'Content-Type': 'application/json'}
    if api_token:
        headers['Authorization'] = f'Bearer {api_token}'
    return headers


async def get_group_root_files(group_id):
    """获取群文件根目录列表"""
    url = f"http://{http_host}:{http_port}/get_group_root_files"
    payload = {"group_id": group_id}
    headers = get_headers()

    print("发送给消息平台->" + str(payload))
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"获取群文件根目录失败，状态码: {response.status}, 错误信息: {await response.text()}")
            res = await response.json()
            if res["status"] != "ok":
                raise Exception(f"获取群文件根目录失败，状态码: {res['status']}\n完整消息: {str(res)}")
            return res["data"]


async def create_group_file_folder(group_id, folder_name):
    """创建群文件夹"""
    url = f"http://{http_host}:{http_port}/create_group_file_folder"

    # 根据平台类型准备不同的请求参数
    if platform_type == 'napcat':
        payload = {
            "group_id": group_id,
            "folder_name": folder_name
        }
    elif platform_type == 'llonebot':
        payload = {
            "group_id": group_id,
            "name": folder_name
        }
    elif platform_type == 'lagrange':
        payload = {
            "group_id": group_id,
            "name": folder_name,
            "parent_id": "/"
        }
    else:
        raise Exception("消息平台配置有误, 只能是'napcat', 'llonebot'或'lagrange'")

    headers = get_headers()
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


async def get_group_folder_id(group_id, folder_name: str = '/'):
    """获取(或创建)群文件夹ID"""
    if folder_name == '/':
        return '/'

    # 尝试查找文件夹
    data = await get_group_root_files(group_id)
    for folder in data.get('folders', []):
        if folder.get('folder_name') == folder_name:
            return folder.get('folder_id')

    # 如果未找到，创建文件夹
    folder_id = await create_group_file_folder(group_id, folder_name)
    if folder_id is None:
        # 再次检查，以防文件夹已创建但未返回ID
        data = await get_group_root_files(group_id)
        for folder in data.get('folders', []):
            if folder.get('folder_name') == folder_name:
                return folder.get('folder_id')
        return "/"
    return folder_id


async def upload_file(ctx, file, name, folder_name='/'):
    is_private = ctx.event.launcher_type == "person"
    target_id = ctx.event.sender_id
    if is_private:  # 私聊
        url = f"http://{http_host}:{http_port}/upload_private_file"
        payload = {
            "user_id": target_id,
            "file": file,
            "name": name
        }
    else:  # 群聊
        url = f"http://{http_host}:{http_port}/upload_group_file"
        folder_id = await get_group_folder_id(target_id, folder_name)
        payload = {
            "group_id": target_id,
            "file": file,
            "name": name,
            "folder_id": folder_id
        }

    headers = get_headers()
    print("发送给消息平台->" + str(payload))

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"上传失败，状态码: {response.status}, 错误信息: {await response.text()}")
            res = await response.json()
            print("消息平台返回->" + str(res))
            if res["status"] != "ok":
                raise Exception(f"上传失败，状态码: {res['status']}\n完整消息: {str(res)}")
            return res.get("data")
