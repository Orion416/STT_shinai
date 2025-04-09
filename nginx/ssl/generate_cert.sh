#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # 无颜色

echo -e "${BLUE}生成自签名SSL证书${NC}"
echo -e "${YELLOW}注意: 这个证书仅用于开发和测试环境，不应在生产环境中使用${NC}"
echo

# 检查openssl是否安装
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}错误: 未找到openssl命令。请先安装openssl:${NC}"
    echo -e "  Ubuntu/Debian: ${BLUE}sudo apt-get install openssl${NC}"
    echo -e "  CentOS/RHEL: ${BLUE}sudo yum install openssl${NC}"
    echo -e "  macOS: ${BLUE}brew install openssl${NC}"
    exit 1
fi

# 设置变量
CERT_NAME="temp_cert"
DAYS=365
KEY_FILE="${CERT_NAME}.key"
CERT_FILE="${CERT_NAME}.crt"

# 询问域名
read -p "请输入证书的域名或IP地址 [默认: localhost]: " DOMAIN
DOMAIN=${DOMAIN:-localhost}

echo -e "${BLUE}生成SSL证书和私钥...${NC}"
echo -e "${YELLOW}域名/IP: ${DOMAIN}${NC}"
echo -e "${YELLOW}有效期: ${DAYS}天${NC}"

# 生成私钥和证书
openssl req -x509 -nodes -days ${DAYS} -newkey rsa:2048 \
    -keyout ${KEY_FILE} -out ${CERT_FILE} \
    -subj "/CN=${DOMAIN}" \
    -addext "subjectAltName=DNS:${DOMAIN},IP:127.0.0.1"

# 检查是否成功
if [ $? -eq 0 ]; then
    echo -e "${GREEN}证书生成成功!${NC}"
    echo -e "私钥文件: ${BLUE}${KEY_FILE}${NC}"
    echo -e "证书文件: ${BLUE}${CERT_FILE}${NC}"

    # 设置权限
    chmod 600 ${KEY_FILE}
    chmod 644 ${CERT_FILE}

    echo -e "${YELLOW}注意: 使用自签名证书时，浏览器会显示安全警告。${NC}"
    echo -e "${YELLOW}      您需要在浏览器中手动接受此证书。${NC}"
else
    echo -e "${RED}证书生成失败!${NC}"
fi
