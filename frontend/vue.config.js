const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  devServer: {
    port: 5001,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5005',
        changeOrigin: true
      }
    },
    client: {
      // 设置动态WebSocket URL，避免HTTPS安全错误
      webSocketURL: {
        hostname: '172.16.1.18',
        pathname: '/ws',
        port: 443,
        protocol: 'wss',
      }
    }
  },
  publicPath: '/',
  lintOnSave: false  // 禁用ESLint检查
}) 