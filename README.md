# Speech-To-Text

基于Faster Whisper的高性能语音转文本系统，支持文件上传和麦克风实时转写。

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![许可证](https://img.shields.io/badge/许可证-MIT-green)

### 初始化项目

首次使用时，需要运行初始化脚本：

```bash
./init.sh
```

此脚本将：
- 创建必要的目录结构
- 复制配置文件模板
- 生成SSL证书
- 检查并安装依赖

### 启动服务

初始化完成后，使用以下命令启动服务：

```bash
./start.sh start
```

使用`start.sh`脚本管理服务：

```bash
# 启动所有服务
./start.sh start

# 停止所有服务
./start.sh stop

# 重启所有服务
./start.sh restart

# 查看服务状态
./start.sh status

# 查看日志
./start.sh logs frontend  # 查看前端日志
./start.sh logs backend   # 查看后端日志
./start.sh logs nginx     # 查看Nginx日志
```

### 访问系统

服务启动后，可通过以下地址访问：

- 前端开发服务器：http://localhost:5001
- HTTP访问（会重定向到HTTPS）：http://localhost:8080
- HTTPS安全访问（支持麦克风功能）：https://localhost:8443

## 项目结构

```
Speech-To-Text/
  ├── backend/          # 后端API和处理逻辑
  │   ├── app.py        # 主应用程序
  │   ├── core/         # 核心处理模块
  │   │   ├── engine.py  # STT引擎实现
  │   │   ├── utils.py   # 工具函数
  │   │   └── __init__.py # 模块初始化
  │   └── requirements.txt # Python依赖
  ├── frontend/         # Vue.js前端应用
  │   ├── src/          # 前端源代码
  │   │   ├── App.vue    # 主组件
  │   │   ├── main.js    # 入口文件
  │   │   └── components/ # 子组件
  │   └── public/       # 静态资源
  ├── nginx/            # Nginx配置文件
  │   ├── nginx.conf    # 主配置文件
  │   └── ssl/          # SSL证书
  ├── samples/          # 示例音频视频文件
  ├── logs/             # 日志文件
  ├── var/              # 变量和临时文件
  ├── .gitignore        # Git忽略文件
  ├── start.sh          # 统一的服务控制脚本
  └── README.md         # 项目说明文档
```

## 配置说明

主要配置文件：

- `.env`：环境变量配置
- `var/config.txt`：系统配置
- `nginx/nginx.conf`：Nginx配置

初始化时会从示例文件创建这些配置文件，您可以根据需要进行修改。

## 文档

详细文档位于`docs/`目录：

- `API.md`：API接口文档
- `DEVELOPMENT.md`：开发指南
- `USER_GUIDE.md`：用户使用指南

## 许可证

本项目采用MIT许可证。详情请参阅LICENSE文件。
