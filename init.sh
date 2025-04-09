#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # 无颜色

echo -e "${BLUE}语音转文本系统 - 初始化脚本${NC}"
echo -e "${YELLOW}此脚本将帮助你初始化项目配置${NC}"
echo

# 检查目录结构
echo -e "${BLUE}检查目录结构...${NC}"
mkdir -p logs var/tmp var/log/nginx

# 复制配置文件
echo -e "${BLUE}设置配置文件...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${GREEN}已创建 .env 文件${NC}"
else
    echo -e "${YELLOW}.env 文件已存在，跳过${NC}"
fi

if [ ! -f "var/config.txt" ]; then
    cp var/config.txt.example var/config.txt
    echo -e "${GREEN}已创建 var/config.txt 文件${NC}"
else
    echo -e "${YELLOW}var/config.txt 文件已存在，跳过${NC}"
fi

# 生成SSL证书
echo -e "${BLUE}检查SSL证书...${NC}"
if [ ! -f "nginx/ssl/temp_cert.key" ] || [ ! -f "nginx/ssl/temp_cert.crt" ]; then
    echo -e "${YELLOW}未找到SSL证书，准备生成...${NC}"
    cd nginx/ssl
    ./generate_cert.sh
    cd ../../
else
    echo -e "${GREEN}SSL证书已存在${NC}"
fi

# 检查conda环境
echo -e "${BLUE}检查conda环境...${NC}"
if command -v conda &> /dev/null; then
    if conda env list | grep -q "speech_to_text"; then
        echo -e "${GREEN}conda环境 'speech_to_text' 已存在${NC}"
    else
        echo -e "${YELLOW}创建conda环境 'speech_to_text'...${NC}"
        conda create -y -n speech_to_text python=3.10
        echo -e "${GREEN}conda环境已创建${NC}"

        echo -e "${YELLOW}安装依赖...${NC}"
        conda activate speech_to_text
        pip install -r backend/requirements.txt

        # 检测CUDA可用性并安装PyTorch
        echo -e "${YELLOW}检测CUDA可用性...${NC}"
        if command -v nvidia-smi &> /dev/null; then
            echo -e "${GREEN}检测到NVIDIA GPU，安装CUDA版PyTorch${NC}"
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
        else
            echo -e "${YELLOW}未检测到NVIDIA GPU，安装CPU版PyTorch${NC}"
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        fi
    fi
else
    echo -e "${RED}未找到conda命令。请先安装Miniconda或Anaconda:${NC}"
    echo -e "  下载地址: ${BLUE}https://docs.conda.io/en/latest/miniconda.html${NC}"
fi

# 检查前端依赖
echo -e "${BLUE}检查前端依赖...${NC}"
if [ -d "frontend/node_modules" ]; then
    echo -e "${GREEN}前端依赖已安装${NC}"
else
    if command -v npm &> /dev/null; then
        echo -e "${YELLOW}安装前端依赖...${NC}"
        cd frontend
        npm install
        cd ..
        echo -e "${GREEN}前端依赖安装完成${NC}"
    else
        echo -e "${RED}未找到npm命令。请先安装Node.js:${NC}"
        echo -e "  下载地址: ${BLUE}https://nodejs.org/${NC}"
    fi
fi

echo
echo -e "${GREEN}初始化完成!${NC}"
echo -e "${YELLOW}你现在可以使用以下命令启动服务:${NC}"
echo -e "  ${BLUE}./start.sh start${NC}"
echo
