#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # 无颜色

# 确定项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${BLUE}项目根目录: ${PROJECT_ROOT}${NC}"

# 配置文件路径
CONFIG_FILE="$PROJECT_ROOT/var/config.txt"

# 默认配置
DEFAULT_MODEL="medium"
DEFAULT_DEVICE="gpu"

# 创建必要的目录
create_directories() {
    echo -e "${BLUE}创建必要的目录...${NC}"
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/var/log/nginx"
    mkdir -p "$PROJECT_ROOT/var/tmp/nginx/client"
    mkdir -p "$PROJECT_ROOT/nginx/logs"

    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}错误: 未找到配置文件 var/config.txt${NC}"
        echo -e "${YELLOW}请运行初始化脚本: ${BLUE}./init.sh${NC}"
        exit 1
    fi

    # 检查SSL证书
    if [ ! -f "$PROJECT_ROOT/nginx/ssl/temp_cert.key" ] || [ ! -f "$PROJECT_ROOT/nginx/ssl/temp_cert.crt" ]; then
        echo -e "${RED}错误: 未找到SSL证书${NC}"
        echo -e "${YELLOW}请运行初始化脚本或生成证书: ${BLUE}cd nginx/ssl && ./generate_cert.sh${NC}"
        exit 1
    fi
}

# 读取配置
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        # 创建默认配置
        mkdir -p "$(dirname "$CONFIG_FILE")"
        echo "WHISPER_MODEL=$DEFAULT_MODEL" > "$CONFIG_FILE"
        echo "WHISPER_DEVICE=$DEFAULT_DEVICE" >> "$CONFIG_FILE"
        WHISPER_MODEL=$DEFAULT_MODEL
        WHISPER_DEVICE=$DEFAULT_DEVICE
    fi
}

# 停止所有服务
stop_services() {
    echo -e "${BLUE}正在停止现有服务...${NC}"

    # 停止前端服务
    if pgrep -f "node.*vue-cli-service serve" > /dev/null; then
        echo -e "${YELLOW}停止前端服务...${NC}"
        pkill -f "node.*vue-cli-service serve"
    fi

    # 停止后端API
    if pgrep -f "python.*app.py --api" > /dev/null; then
        echo -e "${YELLOW}停止后端API服务...${NC}"
        pkill -f "python.*app.py --api"
    fi

    # 检查并停止Nginx
    if pgrep -f "nginx.*nginx.conf" > /dev/null; then
        echo -e "${YELLOW}停止Nginx...${NC}"
        # 尝试使用nginx -s stop方式停止
        nginx -s stop -c "$PROJECT_ROOT/nginx/nginx.conf" -p "$PROJECT_ROOT" 2>/dev/null || \
        # 如果失败，尝试使用sudo -E保留环境变量
        sudo -E nginx -s stop -c "$PROJECT_ROOT/nginx/nginx.conf" -p "$PROJECT_ROOT" 2>/dev/null || \
        # 如果仍然失败，尝试使用pkill
        pkill -f "nginx.*nginx.conf"
    fi

    echo -e "${GREEN}所有服务已停止${NC}"
}

# 启动所有服务
start_services() {
    create_directories
    load_config

    # 先停止所有服务，确保没有冲突
    stop_services

    # 等待所有服务完全停止
    sleep 2

    echo -e "${BLUE}使用模型: $WHISPER_MODEL, 硬件加速: $WHISPER_DEVICE${NC}"

    # 转换GPU设置为布尔值参数
    FORCE_GPU_ARG="False"
    if [ "$WHISPER_DEVICE" = "gpu" ]; then
        FORCE_GPU_ARG="True"
    fi

    # 将模型和设备设置为环境变量
    export WHISPER_MODEL
    export WHISPER_DEVICE

    # 启动Nginx服务
    echo -e "${BLUE}正在启动Nginx服务...${NC}"

    # 创建必要的目录并设置权限
    mkdir -p "$PROJECT_ROOT/var/log/nginx"
    mkdir -p "$PROJECT_ROOT/var/tmp/nginx/client"
    chmod -R 755 "$PROJECT_ROOT/var/log/nginx" "$PROJECT_ROOT/var/tmp/nginx"

    # 启动Nginx
    # 先尝试不使用sudo
    nginx -c "$PROJECT_ROOT/nginx/nginx.conf" -p "$PROJECT_ROOT"
    NGINX_RESULT=$?

    # 如果失败，尝试使用sudo
    if [ $NGINX_RESULT -ne 0 ]; then
        echo -e "${YELLOW}尝试使用sudo启动Nginx...${NC}"
        sudo nginx -c "$PROJECT_ROOT/nginx/nginx.conf" -p "$PROJECT_ROOT"
        NGINX_RESULT=$?
    fi

    if [ $NGINX_RESULT -eq 0 ]; then
        echo -e "${GREEN}Nginx服务启动成功${NC}"
        echo -e "${BLUE}已配置HTTP端口: 8080, HTTPS端口: 8443${NC}"
    else
        echo -e "${RED}Nginx服务启动失败 (错误码: $NGINX_RESULT)${NC}"
        echo -e "${YELLOW}尝试修复方法:${NC}"
        echo -e "1. 检查是否有其他Nginx实例或服务占用了端口"
        echo -e "   ${BLUE}netstat -tulpn | grep '8080\|8443'${NC}"
        echo -e "2. 确保目录权限正确"
        echo -e "   ${BLUE}chmod -R 755 $PROJECT_ROOT/var/log/nginx $PROJECT_ROOT/var/tmp/nginx${NC}"
    fi

    # 启动前端
    echo -e "${BLUE}正在启动前端服务...${NC}"
    cd "$PROJECT_ROOT/frontend"
    nohup npm run serve > "$PROJECT_ROOT/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo -e "${GREEN}前端服务已启动，PID: $FRONTEND_PID${NC}"

    # 等待前端服务启动
    sleep 5

    # 启动后端API
    echo -e "${BLUE}正在启动STT后端API服务...${NC}"
    cd "$PROJECT_ROOT/backend"
    nohup python app.py --api --model "$WHISPER_MODEL" --force_gpu "$FORCE_GPU_ARG" > "$PROJECT_ROOT/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    echo -e "${GREEN}后端API服务已启动，PID: $BACKEND_PID${NC}"

    # 获取服务器IP地址
    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo -e "${GREEN}全部服务启动成功！${NC}"
    echo -e "${BLUE}您可以通过以下地址访问系统:${NC}"
    echo -e "  前端开发服务器: ${GREEN}http://localhost:5001${NC}"
    echo -e "  HTTP访问 (会重定向到HTTPS): ${GREEN}http://$SERVER_IP:8080${NC}"
    echo -e "  HTTPS安全访问 (支持麦克风功能): ${GREEN}https://$SERVER_IP:8443${NC}"
}

# 检查服务状态
check_status() {
    echo -e "${BLUE}检查服务状态...${NC}"

    # 检查前端服务
    if pgrep -f "node.*vue-cli-service serve" > /dev/null; then
        FRONTEND_PID=$(pgrep -f "node.*vue-cli-service serve")
        echo -e "${GREEN}前端服务正在运行，PID: $FRONTEND_PID${NC}"
    else
        echo -e "${RED}前端服务未运行${NC}"
    fi

    # 检查后端API
    if pgrep -f "python.*app.py --api" > /dev/null; then
        BACKEND_PID=$(pgrep -f "python.*app.py --api")
        echo -e "${GREEN}后端API服务正在运行，PID: $BACKEND_PID${NC}"
    else
        echo -e "${RED}后端API服务未运行${NC}"
    fi

    # 检查Nginx
    if pgrep -f "nginx.*nginx.conf" > /dev/null; then
        NGINX_PID=$(pgrep -f "nginx.*master.*nginx.conf")
        echo -e "${GREEN}Nginx服务正在运行，主进程PID: $NGINX_PID${NC}"
    else
        echo -e "${RED}Nginx服务未运行${NC}"
    fi
}

# 查看日志
view_logs() {
    if [ "$1" = "frontend" ]; then
        echo -e "${BLUE}查看前端日志:${NC}"
        tail -n 50 "$PROJECT_ROOT/logs/frontend.log"
    elif [ "$1" = "backend" ]; then
        echo -e "${BLUE}查看后端日志:${NC}"
        tail -n 50 "$PROJECT_ROOT/logs/backend.log"
    elif [ "$1" = "nginx" ]; then
        echo -e "${BLUE}查看Nginx错误日志:${NC}"
        tail -n 50 "$PROJECT_ROOT/var/log/nginx/error.log"
    else
        echo -e "${RED}未指定日志类型，可用选项: frontend, backend, nginx${NC}"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo -e "${BLUE}语音转文本系统 - 服务控制脚本${NC}"
    echo -e "${YELLOW}用法:${NC}"
    echo -e "  $0 ${GREEN}start${NC}         - 启动所有服务"
    echo -e "  $0 ${GREEN}stop${NC}          - 停止所有服务"
    echo -e "  $0 ${GREEN}restart${NC}       - 重启所有服务"
    echo -e "  $0 ${GREEN}status${NC}        - 检查服务状态"
    echo -e "  $0 ${GREEN}logs${NC} ${YELLOW}<type>${NC}    - 查看日志 (frontend, backend, nginx)"
    echo -e "  $0 ${GREEN}help${NC}          - 显示此帮助信息"
}

# 主函数
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        check_status
        ;;
    logs)
        view_logs "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo -e "${RED}未知命令: $1${NC}"
        show_help
        exit 1
        ;;
esac

exit 0
