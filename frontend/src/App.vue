<!--
语音转文本系统 - 前端实现
基于Vue.js和Element Plus的现代化用户界面，支持文件上传和麦克风录音
-->

<template>
  <!-- 主容器 -->
  <div class="app-container">
    <!-- 卡片式布局 -->
    <el-card class="app-card">
      <!-- 卡片头部 -->
      <template #header>
        <div class="card-header">
          <h2>语音转文本</h2>
        </div>
      </template>

      <!-- 标签页导航 -->
      <el-tabs v-model="activeTab">
        <!-- 文件上传标签页 -->
        <el-tab-pane label="文件上传" name="upload">
          <div class="upload-container">
            <!-- 文件上传组件 -->
            <el-upload
              class="upload-area"
              drag
              action="#"
              :auto-upload="false"
              :on-change="handleFileChange"
              :limit="1"
              accept="audio/*,video/*"
            >
              <el-icon class="el-icon--upload"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽音频/视频文件到此处，或<em>点击上传</em>
              </div>
              <template #tip>
                <div class="el-upload__tip">
                  支持的格式：MP3, WAV, FLAC, MP4, AVI 等音视频格式
                </div>
              </template>
            </el-upload>

            <!-- 文件信息显示 -->
            <div class="file-info" v-if="selectedFile">
              <p>已选择文件: {{ selectedFile.name }}</p>
            </div>

            <!-- 转录按钮 -->
            <el-button
              type="primary"
              @click="uploadFile"
              :disabled="!selectedFile || isProcessing"
              :loading="isProcessing"
            >
              {{ isProcessing ? '转录中...' : '开始转录' }}
            </el-button>
          </div>
        </el-tab-pane>

        <!-- 麦克风录音标签页 -->
        <el-tab-pane label="麦克风录音" name="record">
          <div class="record-container">
            <!-- 录音状态指示器 -->
            <div class="record-status">
              <div :class="['status-indicator', recording ? 'recording' : '']"></div>
              <span>{{ recordingStatus }}</span>
            </div>

            <!-- 录音控制按钮 -->
            <div class="record-controls">
              <el-button
                type="primary"
                @click="toggleRecording"
                :disabled="isProcessing && !recording"
                :loading="isProcessing && !recording"
              >
                {{ recording ? '停止录音' : '开始录音' }}
              </el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <!-- 结果展示区域 -->
      <div class="result-container">
        <h3>处理状态:</h3>
        <el-card class="transcription-card">
          <!-- 处理中状态 -->
          <div v-if="isProcessing">
            <p><el-icon class="is-loading"><loading /></el-icon> 正在处理音频文件，请稍候...</p>
          </div>
          <!-- 转录结果 -->
          <div v-else-if="transcription">
            <h4>转录结果:</h4>
            <p>{{ transcription }}</p>
          </div>
          <!-- 初始状态 -->
          <div v-else>
            <p>请上传文件或录制音频后点击开始转录</p>
          </div>
        </el-card>
        <!-- 结果操作按钮 -->
        <div class="action-buttons" v-if="transcription">
          <el-button type="primary" @click="copyText">复制文本</el-button>
          <el-button @click="clearResult">清除</el-button>
        </div>
      </div>

      <!-- 分隔线 -->
      <el-divider>
        <el-icon><info-filled /></el-icon>
      </el-divider>

      <!-- 浏览器兼容性检查组件 -->
      <browser-check v-if="showCompatCheck" />

      <!-- 兼容性检查按钮 -->
      <div class="compatibility-actions" v-if="!showCompatCheck">
        <el-button type="info" @click="showCompatCheck = true">检查浏览器兼容性</el-button>
      </div>
    </el-card>
  </div>
</template>

<script>
// 导入依赖
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { UploadFilled, Loading, InfoFilled } from '@element-plus/icons-vue'
import BrowserCheck from './components/BrowserCheck.vue'

// 为旧版浏览器提供媒体设备API的polyfill
const mediaDevices = navigator.mediaDevices ||
  ((navigator.mozGetUserMedia || navigator.webkitGetUserMedia) ? {
    getUserMedia: function(c) {
      return new Promise(function(y, n) {
        (navigator.mozGetUserMedia || navigator.webkitGetUserMedia).call(navigator, c, y, n);
      });
    }
  } : null);

export default {
  name: 'App',
  components: {
    UploadFilled,
    Loading,
    InfoFilled,
    BrowserCheck
  },
  data() {
    return {
      activeTab: 'upload',          // 当前激活的标签页
      selectedFile: null,           // 选中的文件
      recording: false,             // 是否正在录音
      mediaRecorder: null,          // 媒体录制器实例
      audioChunks: [],              // 录制的音频数据块
      transcription: '',            // 转录结果文本
      isProcessing: false,          // 是否正在处理
      audioBlob: null,              // 音频Blob对象
      browserSupported: !!mediaDevices, // 浏览器是否支持媒体API
      showCompatCheck: false        // 是否显示兼容性检查
    }
  },
  mounted() {
    // 检查浏览器兼容性
    if (!this.browserSupported) {
      ElMessage.warning('您的浏览器可能不支持麦克风录音功能。建议使用Chrome、Firefox或Edge最新版本。');
    } else {
      console.log('浏览器支持媒体录制API');
    }
  },
  computed: {
    // 录音状态文本
    recordingStatus() {
      if (!this.browserSupported) {
        return '您的浏览器不支持录音功能';
      }
      return this.recording ? '正在录音...' : '准备录音';
    }
  },
  methods: {
    // 文件上传相关方法
    handleFileChange(file) {
      this.selectedFile = file.raw

      // 检查文件大小，最大允许100MB
      const maxSize = 100 * 1024 * 1024 // 100MB
      if (file.raw.size > maxSize) {
        ElMessage.warning(`文件过大，当前大小: ${(file.raw.size / 1024 / 1024).toFixed(2)}MB，最大允许: 100MB`)
      }
    },
    async uploadFile() {
      if (!this.selectedFile) {
        ElMessage.warning('请先选择文件')
        return
      }

      // 再次检查文件大小
      const maxSize = 100 * 1024 * 1024 // 100MB
      if (this.selectedFile.size > maxSize) {
        ElMessage.error(`文件过大无法上传，当前大小: ${(this.selectedFile.size / 1024 / 1024).toFixed(2)}MB，最大允许: 100MB`)
        return
      }

      this.isProcessing = true
      this.transcription = '' // 清空之前的转录结果
      const formData = new FormData()
      formData.append('file', this.selectedFile)

      try {
        console.log('发送请求到API...', this.selectedFile.name)
        ElMessage.info('开始处理文件，这可能需要几分钟时间...')

        // 发送文件到后端API进行转录
        const response = await axios.post('/api/transcribe', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 300000 // 5分钟超时，处理大文件
        })

        console.log('API响应:', response.data)

        if (response.data.success) {
          this.transcription = response.data.transcription || '转录成功但结果为空'
          ElMessage.success('转录完成')
        } else {
          ElMessage.error('转录失败：' + (response.data.error || '未知错误'))
          this.transcription = '转录失败: ' + (response.data.error || '未知错误')
        }
      } catch (error) {
        console.error('API请求错误:', error)

        // 错误处理
        if (error.response) {
          // 服务器返回了错误状态码
          if (error.response.status === 413) {
            ElMessage.error('文件过大，超过服务器允许的大小限制 (100MB)')
          } else if (error.response.status === 500) {
            ElMessage.error('服务器内部错误: ' + (error.response.data?.error || '未知错误'))
          } else {
            ElMessage.error(`请求错误 (${error.response.status}): ` + (error.response.data?.error || error.message))
          }
        } else if (error.request) {
          // 请求发出但没有收到响应
          ElMessage.error('服务器无响应，请检查网络连接或服务器状态')
        } else {
          // 请求配置出错
          ElMessage.error('请求配置错误: ' + error.message)
        }

        this.transcription = '请求错误: ' + error.message
      } finally {
        this.isProcessing = false
      }
    },

    // 麦克风录音相关方法
    async toggleRecording() {
      if (this.recording) {
        await this.stopRecording();
      } else {
        await this.startRecording();
      }
    },
    async startRecording() {
      try {
        if (!mediaDevices || !mediaDevices.getUserMedia) {
          ElMessage.error('您的浏览器不支持录音功能，请使用Chrome、Firefox或Edge最新版本');
          return;
        }

        // 获取麦克风权限
        const stream = await mediaDevices.getUserMedia({ audio: true });

        // 初始化媒体录制器
        if (typeof MediaRecorder === 'undefined') {
          ElMessage.error('您的浏览器不支持MediaRecorder API，请更新浏览器版本');
          return;
        }

        try {
          this.mediaRecorder = new MediaRecorder(stream);
        } catch (e) {
          console.error('创建MediaRecorder失败:', e);
          ElMessage.error('创建录音器失败: ' + e.message);
          return;
        }

        this.audioChunks = [];

        this.mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            this.audioChunks.push(event.data);
          }
        };

        this.mediaRecorder.onstop = async () => {
          if (this.audioChunks.length > 0) {
            this.audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
            await this.sendAudioToServer();
          } else {
            ElMessage.warning('未录制到音频数据');
          }
        };

        this.mediaRecorder.onerror = (e) => {
          console.error('录音出错:', e);
          ElMessage.error('录音出错: ' + e.message);
        };

        // 开始录音
        this.mediaRecorder.start(1000); // 每秒触发一次ondataavailable事件
        this.recording = true;

        // 显示录音状态
        ElMessage.success('录音已开始，请对着麦克风说话');
      } catch (error) {
        console.error('麦克风访问错误:', error);
        ElMessage.error('无法访问麦克风: ' + error.message);

        // 尝试提供更具体的错误信息
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
          ElMessage.error('麦克风权限被拒绝，请在浏览器设置中允许访问麦克风');
        } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
          ElMessage.error('未检测到麦克风设备，请确认麦克风已正确连接');
        } else if (error.name === 'NotReadableError' || error.name === 'TrackStartError') {
          ElMessage.error('麦克风被其他应用程序占用，请关闭可能使用麦克风的其他应用');
        }
      }
    },
    stopRecording() {
      if (this.mediaRecorder && this.recording) {
        this.mediaRecorder.stop()
        this.recording = false

        // 关闭麦克风
        this.mediaRecorder.stream.getTracks().forEach(track => track.stop())
      }
    },
    async sendAudioToServer() {
      if (!this.audioBlob) {
        ElMessage.warning('没有录音数据')
        return
      }

      // 检查录音大小
      const maxSize = 100 * 1024 * 1024 // 100MB
      if (this.audioBlob.size > maxSize) {
        ElMessage.error(`录音文件过大，当前大小: ${(this.audioBlob.size / 1024 / 1024).toFixed(2)}MB，最大允许: 100MB`)
        return
      }

      this.isProcessing = true
      const formData = new FormData()
      formData.append('audio', this.audioBlob, 'recording.wav')

      try {
        console.log('发送录音数据到API..., 大小:', (this.audioBlob.size / 1024).toFixed(2), 'KB')

        const response = await axios.post('/api/transcribe-blob', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          timeout: 300000 // 5分钟超时
        })

        if (response.data.success) {
          this.transcription = response.data.transcription
          ElMessage.success('转录完成')
        } else {
          ElMessage.error('转录失败：' + (response.data.error || '未知错误'))
          this.transcription = '转录失败: ' + (response.data.error || '未知错误')
        }
      } catch (error) {
        console.error('API请求错误:', error)

        // 针对不同错误类型提供更具体的错误信息
        if (error.response) {
          // 服务器返回了错误状态码
          if (error.response.status === 413) {
            ElMessage.error('录音文件过大，超过服务器允许的大小限制')
          } else if (error.response.status === 500) {
            ElMessage.error('服务器内部错误: ' + (error.response.data?.error || '未知错误'))
          } else {
            ElMessage.error(`请求错误 (${error.response.status}): ` + (error.response.data?.error || error.message))
          }
        } else if (error.request) {
          // 请求发出但没有收到响应
          ElMessage.error('服务器无响应，请检查网络连接或服务器状态')
        } else {
          // 请求配置出错
          ElMessage.error('请求配置错误: ' + error.message)
        }

        this.transcription = '请求错误: ' + error.message
      } finally {
        this.isProcessing = false
      }
    },

    // 结果相关方法
    copyText() {
      if (this.transcription) {
        navigator.clipboard.writeText(this.transcription)
          .then(() => {
            ElMessage.success('已复制到剪贴板')
          })
          .catch(() => {
            ElMessage.error('复制失败')
          })
      }
    },
    clearResult() {
      this.transcription = ''
      this.selectedFile = null
      this.audioBlob = null

      // 重置上传组件
      const uploadComponent = document.querySelector('.el-upload')
      if (uploadComponent) {
        const uploadFiles = uploadComponent.__vue__?.uploadFiles
        if (uploadFiles) {
          uploadFiles.length = 0
        }
      }
    }
  }
}
</script>

<style>
.app-container {
  max-width: 900px;
  margin: 20px auto;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif;
}

.app-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: center;
  align-items: center;
  color: #606266;
}

.upload-container, .record-container {
  padding: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-area {
  width: 100%;
  max-width: 400px;
}

.file-info {
  margin: 15px 0;
  color: #606266;
}

.record-status {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.status-indicator {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background-color: #67c23a;
  margin-right: 10px;
  opacity: 0.3;
}

.status-indicator.recording {
  opacity: 1;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
  100% {
    opacity: 1;
  }
}

.result-container {
  margin-top: 30px;
  border-top: 1px solid #ebeef5;
  padding-top: 20px;
}

.transcription-card {
  margin: 15px 0;
  background-color: #f5f7fa;
}

.transcription-card p {
  white-space: pre-wrap;
  word-break: break-all;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
}

.action-buttons .el-button {
  margin-left: 15px;
}

.compatibility-actions {
  display: flex;
  justify-content: center;
  margin: 15px 0;
}

.el-divider {
  margin: 30px 0;
}
</style>