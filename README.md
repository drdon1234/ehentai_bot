# 适配langbot的ehentai转pdf插件 #

安装方法  
[1] langbot配置完毕后使用管理员账号对bot发送以下指令
```
!plugin get https://github.com/exneverbur/ShowMeJM
```
[2]  
```"langbot webui" -> "插件" -> "+ 安装" -> 输入"https://github.com/drdon1234/ehentai_bot" -> "安装"```


使用说明
```
指令帮助：
  [1] 搜索画廊: 搜eh [关键词] [最低评分（2-5，默认2）] [最少页数（默认1）] [获取第几页的画廊列表（默认1）]
  [2] 下载画廊: 看eh [画廊链接]
  [3] 获取指令帮助: eh

可用的搜索方式:
  [1] 搜eh [关键词]
  [2] 搜eh [关键词] [最低评分] [最少页数]
  [3] 搜eh [关键词] [最低评分] [最少页数] [获取第几页的画廊列表]
  
PS:
  ehentai的分页目录仅能通过迭代生成，不建议获取较大页数的画廊列表
```

使用前请先修改配置文件config.yaml
```
platform:
  type: "napcat" # 消息平台，兼容napcat, llonebot, lagrange
  http_host: "192.168.5.2" # 非docker部署一般为127.0.0.1，docker部署一般为宿主机局域网ip
  http_port: 13000 # 消息平台监听端口，通常为3000或2333
  api_token: "" # http服务器token，没有则不填

request:
  headers:
    User-Agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
  proxies: "http://192.168.5.2:17893" # 墙内用户必填项，非docker部署clash一般为http://127.0.0.1:port，docker部署clash一般为http://{宿主机局域网ip}:port
  concurrency: 5 # 并发数量限制，在我的机器上超过5偶尔会有图片丢失问题
  max_retries: 3 # 请求重试次数
  timeout: 10 # 超时时间

output:
  image_folder: "/app/sharedFolder/tempImages" # 暂时存放画廊图片的文件夹路径
  pdf_folder: "/app/sharedFolder/ehentai" # 存放pdf文件的路径
  jpeg_quality: 85 # 图片质量，100为不压缩，85左右可以达到文件大小和质量的最佳平衡
  max_pages_per_pdf: 200 # 单个pdf文件最大页数

# 注意：
# 如果你是docker部署，请务必为消息平台容器挂载pdf文件所在的文件夹，否则消息平台将无法解析文件路径
#
# 我是这样做的：
#   对langbot: /vol3/1000/dockerSharedFolder -> /app/sharedFolder
#   对napcat: /vol3/1000/dockerSharedFolder -> /app/sharedFolder
```
