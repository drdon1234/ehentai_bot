# 适配 LangBot 的 EHentai画廊 转 PDF 插件

## 安装方法

1. **使用管理员账号安装插件**  
在 LangBot 配置完毕后，使用管理员账号对 Bot 发送以下指令：
```
!plugin get https://github.com/exneverbur/ShowMeJM
```
2. **通过 WebUI 安装插件**  
- 打开 "LangBot WebUI" -> "插件" -> "+ 安装"  
- 输入以下地址并点击安装：
```
https://github.com/drdon1234/ehentai_bot
```

---

## 使用说明

### 指令帮助

- **搜索画廊**  
```搜eh [关键词] [最低评分（2-5，默认2）] [最少页数（默认1）] [获取第几页的画廊列表（默认1）]```

- **下载画廊**  
```看eh [画廊链接]```

- **获取指令帮助**  
```eh```

### 可用的搜索方式

1. 基础搜索：  
```搜eh [关键词]```

2. 高级搜索：  
```搜eh [关键词] [最低评分] [最少页数]```

3. 搜索指定页：  
~~```搜eh [关键词] [最低评分] [最少页数] [获取第几页的画廊列表]```~~(有已知bug，等待修复)

**注意：**  
- 搜索使用的多关键词使用以下符号连接`,` `，` `+`，关键词之间不要添加任何空格
- EHentai 的分页目录仅能通过迭代生成，建议避免获取较大页数的画廊列表。

---

## 配置文件修改

使用前请先修改配置文件 `config.yaml`：

### 平台设置
```
platform:
  type: "napcat" # 消息平台，兼容 napcat, llonebot, lagrange
  http_host: "192.168.5.2" # 非 docker 部署一般为 127.0.0.1，docker 部署一般为宿主机局域网 IP
  http_port: 13000 # 消息平台监听端口，通常为 3000 或 2333
  api_token: "" # HTTP 服务器 token，没有则不填
```

### 请求设置
```
request:
  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
  proxies: "http://192.168.5.2:17893" # 墙内用户必填项，代理软件位于宿主机时，非docker部署一般为http://127.0.0.1:port，docker部署一般为http://{宿主机局域网ip}:port
  concurrency: 5 # 并发数量限制，在我的机器上超过5偶尔会有图片丢失问题
  max_retries: 3 # 请求重试次数
  timeout: 10 # 超时时间
```

### 输出设置
```
output:
  image_folder: "/app/sharedFolder/tempImages" # 暂时存放画廊图片的文件夹路径
  pdf_folder: "/app/sharedFolder/ehentai" # 存放 PDF 文件的路径
  jpeg_quality: 85 # 图片质量，100 为不压缩，85 左右可以达到文件大小和质量的最佳平衡
  max_pages_per_pdf: 200 # 单个 PDF 文件最大页数
```

---

## Docker 部署注意事项

如果您是 Docker 部署，请务必为消息平台容器挂载 PDF 文件所在的文件夹，否则消息平台将无法解析文件路径。

示例挂载方式(NapCat)：
- 对 LangBot：`/vol3/1000/dockerSharedFolder -> /app/sharedFolder`
- 对 NapCat：`/vol3/1000/dockerSharedFolder -> /app/sharedFolder`

---

## 已知 BUG

- 搜索指定页不可用
- 在画廊仅有一页时获取子分页错误

---

## 开发中的功能

- 请求结构中添加cookie选项以访问里站
- 随机画廊
- 重构项目以增加可读性
