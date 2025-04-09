<template>
  <div class="compatibility-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <h3>浏览器兼容性检查</h3>
        </div>
      </template>
      
      <div class="check-list">
        <div class="check-item">
          <div class="status-icon">
            <el-icon :color="checks.mediaDevices ? '#67C23A' : '#F56C6C'">
              <component :is="checks.mediaDevices ? 'CircleCheckFilled' : 'CircleCloseFilled'" />
            </el-icon>
          </div>
          <div class="check-text">
            <div class="check-title">MediaDevices API</div>
            <div class="check-description">{{ checks.mediaDevices ? '支持' : '不支持' }}</div>
          </div>
        </div>
        
        <div class="check-item">
          <div class="status-icon">
            <el-icon :color="checks.mediaRecorder ? '#67C23A' : '#F56C6C'">
              <component :is="checks.mediaRecorder ? 'CircleCheckFilled' : 'CircleCloseFilled'" />
            </el-icon>
          </div>
          <div class="check-text">
            <div class="check-title">MediaRecorder API</div>
            <div class="check-description">{{ checks.mediaRecorder ? '支持' : '不支持' }}</div>
          </div>
        </div>
        
        <div class="check-item">
          <div class="status-icon">
            <el-icon :color="checks.secure ? '#67C23A' : '#F56C6C'">
              <component :is="checks.secure ? 'CircleCheckFilled' : 'CircleCloseFilled'" />
            </el-icon>
          </div>
          <div class="check-text">
            <div class="check-title">安全上下文</div>
            <div class="check-description">{{ checks.secure ? '安全连接 (HTTPS/localhost)' : '非安全连接 (HTTP)' }}</div>
          </div>
        </div>
        
        <div class="check-item">
          <div class="status-icon">
            <el-icon :color="micPermissionStatus.color">
              <component :is="micPermissionStatus.icon" />
            </el-icon>
          </div>
          <div class="check-text">
            <div class="check-title">麦克风访问</div>
            <div class="check-description">{{ micPermissionStatus.text }}</div>
          </div>
          <div class="check-action" v-if="micPermissionStatus.needsCheck">
            <el-button size="small" @click="checkMicPermission">检查权限</el-button>
          </div>
        </div>
      </div>
      
      <div class="browser-info">
        <h4>您的浏览器信息</h4>
        <p>{{ userAgent }}</p>
      </div>
      
      <div class="recommendations" v-if="!allChecksPass">
        <h4>推荐操作</h4>
        <ul>
          <li v-if="!checks.mediaDevices || !checks.mediaRecorder">
            建议使用支持MediaRecorder API的浏览器，如Chrome 47+、Firefox 25+、Edge 79+
          </li>
          <li v-if="!checks.secure">
            通过IP地址访问时，Chrome会限制麦克风访问。请尝试：<br>
            1. 在同一台电脑上使用 <a href="http://localhost:5001">http://localhost:5001</a> 访问<br>
            2. 或在Chrome地址栏点击锁图标，手动允许麦克风访问
          </li>
          <li v-if="micPermissionStatus.status === 'denied'">
            请在Chrome地址栏右侧点击锁/信息图标，找到并重置麦克风权限设置
          </li>
          <li v-if="micPermissionStatus.status === 'unavailable'">
            请检查麦克风是否正确连接，并且没有被其他应用程序占用
          </li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script>
import { CircleCheckFilled, CircleCloseFilled, WarningFilled } from '@element-plus/icons-vue'

export default {
  name: 'BrowserCheck',
  components: {
    CircleCheckFilled,
    CircleCloseFilled,
    WarningFilled
  },
  data() {
    return {
      checks: {
        mediaDevices: !!navigator.mediaDevices,
        mediaRecorder: typeof MediaRecorder !== 'undefined',
        secure: window.location.protocol === 'https:' || 
               window.location.hostname === 'localhost' ||
               window.location.hostname.startsWith('192.168.') ||
               window.location.hostname.startsWith('10.') ||
               window.location.hostname.startsWith('172.16.')
      },
      micPermission: {
        status: 'unknown', // 'unknown', 'granted', 'denied', 'unavailable'
        lastChecked: null
      },
      userAgent: navigator.userAgent
    }
  },
  computed: {
    micPermissionStatus() {
      switch(this.micPermission.status) {
        case 'granted':
          return {
            text: '已允许访问',
            color: '#67C23A',
            icon: 'CircleCheckFilled',
            needsCheck: false
          };
        case 'denied':
          return {
            text: '访问被拒绝',
            color: '#F56C6C',
            icon: 'CircleCloseFilled',
            needsCheck: false
          };
        case 'unavailable':
          return {
            text: '麦克风不可用',
            color: '#F56C6C',
            icon: 'CircleCloseFilled',
            needsCheck: false
          };
        default:
          return {
            text: '未检查',
            color: '#E6A23C',
            icon: 'WarningFilled',
            needsCheck: true
          };
      }
    },
    allChecksPass() {
      return this.checks.mediaDevices && 
             this.checks.mediaRecorder && 
             this.checks.secure && 
             this.micPermission.status === 'granted';
    }
  },
  methods: {
    async checkMicPermission() {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          this.micPermission.status = 'unavailable';
          return;
        }
        
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.micPermission.status = 'granted';
        this.micPermission.lastChecked = new Date();
        
        // 释放麦克风
        stream.getTracks().forEach(track => track.stop());
      } catch (error) {
        console.error('麦克风检查错误:', error);
        
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          this.micPermission.status = 'denied';
        } else {
          this.micPermission.status = 'unavailable';
        }
        
        this.micPermission.lastChecked = new Date();
      }
    }
  }
}
</script>

<style scoped>
.compatibility-container {
  max-width: 800px;
  margin: 20px auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.check-list {
  margin-bottom: 20px;
}

.check-item {
  display: flex;
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.status-icon {
  margin-right: 12px;
  display: flex;
  align-items: center;
  font-size: 22px;
}

.check-text {
  flex-grow: 1;
}

.check-title {
  font-weight: bold;
  margin-bottom: 4px;
}

.check-description {
  color: #606266;
  font-size: 14px;
}

.check-action {
  display: flex;
  align-items: center;
}

.browser-info {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.browser-info h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.browser-info p {
  margin: 0;
  word-break: break-all;
  font-size: 14px;
  color: #606266;
}

.recommendations {
  border-top: 1px solid #ebeef5;
  padding-top: 15px;
}

.recommendations h4 {
  margin-top: 0;
}

.recommendations ul {
  padding-left: 20px;
}

.recommendations li {
  margin-bottom: 8px;
  color: #606266;
}
</style> 