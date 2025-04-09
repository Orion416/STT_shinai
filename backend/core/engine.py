"""
语音转文字引擎核心实现
基于Faster Whisper模型，支持GPU加速
整合了engine.py和stt_engine.py的功能
"""

import os
import time
import tempfile
import logging
import torch
import numpy as np
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from faster_whisper import WhisperModel

# 导入工具函数
from .utils import normalize_audio, read_audio_file, is_video_file, convert_video_to_audio, cleanup_temp_files

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("STT_Engine")

# 支持的视频格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm']

class STTEngine:
    """语音转文字引擎，封装Faster Whisper模型"""

    def __init__(
        self,
        model_size: str = "medium",
        use_gpu: bool = True,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        download_root: Optional[str] = None,
        cpu_threads: Optional[int] = None,
        language: Optional[str] = None
    ):
        """
        初始化语音转文字引擎

        Args:
            model_size: 模型大小 ('tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3')
            use_gpu: 是否尝试使用GPU
            device: 手动指定设备 ('cuda', 'cpu', 'cuda:0'等)
            compute_type: 计算精度 ('float16', 'float32', 'int8', 'int8_float16')
            download_root: 模型下载路径
            cpu_threads: CPU线程数 (仅用于CPU模式)
            language: 默认语言代码，如'zh', 'en'等 (None为自动检测)
        """
        self.model_size = model_size
        self.use_gpu = use_gpu
        self.device = device
        self.compute_type = compute_type
        self.download_root = download_root or os.path.expanduser("~/.cache/whisper")
        self.cpu_threads = cpu_threads or os.cpu_count() or 4
        self.language = language
        self.sample_rate = 16000  # 固定采样率

        # 录音参数
        self.channels = 1  # 单声道

        # 加载模型
        self._load_model()

    def _load_model(self) -> None:
        """加载并初始化Whisper模型，自动处理设备选择"""
        logger.info(f"正在加载Faster Whisper模型: {self.model_size}")

        # 如果没有明确指定设备，则自动选择
        if self.device is None:
            self.device = "cuda" if self.use_gpu and self._is_cuda_available() else "cpu"

        # 如果没有明确指定计算类型，则根据设备和模型大小自动选择
        if self.compute_type is None:
            if self.device == "cuda":
                self.compute_type = "float16"  # GPU默认使用float16
            else:
                # CPU上根据模型大小选择不同的计算类型
                self.compute_type = "int8" if self.model_size in ["medium", "large-v1", "large-v2", "large-v3"] else "int8_float16"

        # 尝试加载模型，如果失败则尝试不同的配置
        success = False
        error_messages = []

        # 主要加载尝试
        try:
            logger.info(f"尝试使用设备{self.device}加载模型，计算类型: {self.compute_type}")

            kwargs = {"model_size": self.model_size,
                      "device": self.device,
                      "compute_type": self.compute_type,
                      "download_root": self.download_root}

            # 仅在CPU模式下添加cpu_threads参数
            if self.device == "cpu":
                kwargs["cpu_threads"] = self.cpu_threads

            self.model = WhisperModel(**kwargs)
            logger.info(f"模型加载成功：使用{self.device.upper()}，计算精度为{self.compute_type}")
            success = True
        except Exception as e:
            error_message = f"首次加载失败({self.device}/{self.compute_type}): {str(e)}"
            logger.warning(error_message)
            error_messages.append(error_message)

        # 如果首次加载失败，尝试备选方案
        if not success:
            fallback_configs = []

            # GPU备选方案
            if self.device == "cuda":
                fallback_configs.extend([
                    {"device": "cuda", "compute_type": "int8_float16"},
                    {"device": "cuda", "compute_type": "int8"},
                    {"device": "cpu", "compute_type": "int8"}
                ])
            # CPU备选方案
            else:
                fallback_configs.extend([
                    {"device": "cpu", "compute_type": "int8_float16"},
                    {"device": "cpu", "compute_type": "int8"}
                ])

            # 尝试备选方案
            for config in fallback_configs:
                try:
                    device, compute_type = config["device"], config["compute_type"]
                    logger.info(f"尝试备选配置: {device}/{compute_type}")

                    kwargs = {"model_size": self.model_size,
                              "device": device,
                              "compute_type": compute_type,
                              "download_root": self.download_root}

                    if device == "cpu":
                        kwargs["cpu_threads"] = self.cpu_threads

                    self.model = WhisperModel(**kwargs)

                    # 更新设备和计算类型
                    self.device = device
                    self.compute_type = compute_type

                    logger.info(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")
                    success = True
                    break
                except Exception as e:
                    error_message = f"备选配置加载失败({device}/{compute_type}): {str(e)}"
                    logger.warning(error_message)
                    error_messages.append(error_message)

        # 如果所有尝试都失败，改用最小的模型
        if not success and self.model_size != "tiny":
            try:
                logger.warning("尝试加载最小的tiny模型...")
                self.model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=self.download_root)
                self.model_size = "tiny"
                self.device = "cpu"
                self.compute_type = "int8"
                logger.info("成功加载tiny模型 (CPU/int8)")
                success = True
            except Exception as e:
                error_message = f"加载tiny模型也失败: {str(e)}"
                logger.error(error_message)
                error_messages.append(error_message)

        # 如果所有尝试都失败，抛出异常
        if not success:
            raise RuntimeError(f"无法加载任何Whisper模型\n详细错误: {', '.join(error_messages)}")

    def _is_cuda_available(self) -> bool:
        """检查CUDA是否可用并能创建张量"""
        try:
            if not torch.cuda.is_available():
                logger.info("CUDA不可用")
                return False

            # 尝试创建CUDA张量来确认GPU正常工作
            try:
                test_tensor = torch.zeros(1).cuda()
                test_tensor = test_tensor + 1
                test_tensor.cpu()
                logger.info("CUDA测试成功: GPU工作正常")
                return True
            except Exception as e:
                logger.warning(f"CUDA测试失败: {e}")
                return False
        except Exception as e:
            logger.warning(f"检查CUDA时出错: {e}")
            return False

    def transcribe(
        self,
        audio_input: Union[str, np.ndarray],
        language: Optional[str] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """
        转写音频为文本

        Args:
            audio_input: 音频文件路径或音频数组
            language: 语言代码 (例如 'zh' 表示中文)，默认自动检测
            **kwargs: 传递给Whisper模型的其他参数

        Returns:
            转写结果文本和详细信息字典
        """
        # 转写参数默认值
        transcribe_params = {
            "beam_size": 3,
            "language": language or self.language,
            "vad_filter": True,
            "vad_parameters": dict(min_silence_duration_ms=500),
            "condition_on_previous_text": False
        }

        # 更新用户提供的参数
        transcribe_params.update(kwargs)

        # 处理输入
        temp_file = None
        try:
            # 如果输入是numpy数组，保存为临时文件
            if isinstance(audio_input, np.ndarray):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    temp_file = tmp.name
                sf.write(temp_file, audio_input, self.sample_rate)
                audio_path = temp_file
            else:
                audio_path = audio_input

            # 如果是视频文件，提取音频
            if isinstance(audio_path, str) and self._is_video_file(audio_path):
                logger.info(f"检测到视频文件: {audio_path}，提取音频...")
                audio_path = self._extract_audio_from_video(audio_path)

            # 执行转写
            logger.info(f"开始转写: {audio_path}")
            segments, info = self.model.transcribe(audio_path, **transcribe_params)

            # 合并片段文本
            text = " ".join([segment.text for segment in segments])

            # 创建详细信息字典
            details = {
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "all_languages_probs": info.all_language_probs,
                "segments_count": sum(1 for _ in segments),
                "model_size": self.model_size,
                "device": self.device,
                "compute_type": self.compute_type
            }

            logger.info(f"转写完成: 检测到语言 '{info.language}'，置信度 {info.language_probability:.2f}")

            return text, details

        finally:
            # 清理临时文件
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def _is_video_file(self, file_path: str) -> bool:
        """检查文件是否为支持的视频格式"""
        ext = Path(file_path).suffix.lower()
        return ext in SUPPORTED_VIDEO_FORMATS

    def _extract_audio_from_video(self, video_path: str) -> str:
        """从视频中提取音频，返回临时音频文件路径"""
        # 延迟导入moviepy以减少启动时间
        import moviepy.editor as mp

        temp_dir = tempfile.gettempdir()
        video_filename = Path(video_path).stem
        audio_file = os.path.join(temp_dir, f"{video_filename}_audio.wav")

        try:
            logger.info(f"开始从视频提取音频: {video_path}")
            video = mp.VideoFileClip(video_path)
            video.audio.write_audiofile(audio_file, logger=None)
            logger.info(f"音频提取完成: {audio_file}")
            return audio_file
        except Exception as e:
            logger.error(f"音频提取失败: {e}")
            raise RuntimeError(f"无法从视频提取音频: {str(e)}")

    def record_audio(self, duration: int = 5) -> np.ndarray:
        """
        使用麦克风录制音频

        Args:
            duration: 录制时长（秒）

        Returns:
            录制的音频数据
        """
        # 延迟导入sounddevice以减少启动时间
        import sounddevice as sd

        logger.info(f"开始录制音频，时长{duration}秒...")
        audio_data = sd.rec(
            int(self.sample_rate * duration),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32'
        )
        sd.wait()  # 等待录制完成
        logger.info("录制完成")
        return audio_data

    def save_audio(self, audio_data: np.ndarray, filename: str = "recording.wav") -> str:
        """保存音频数据到文件"""
        sf.write(filename, audio_data, self.sample_rate)
        logger.info(f"音频已保存到: {filename}")
        return filename

    def transcribe_microphone(self, duration: int = 5, **kwargs) -> Tuple[str, Dict[str, Any]]:
        """
        直接录制麦克风音频并转写

        Args:
            duration: 录制时长（秒）
            **kwargs: 传递给transcribe方法的参数

        Returns:
            转写结果文本和详细信息字典
        """
        audio_data = self.record_audio(duration)
        return self.transcribe(audio_data, **kwargs)

    def get_available_models(self) -> List[str]:
        """返回可用的模型列表"""
        return ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"]

    def get_status(self) -> Dict[str, Any]:
        """返回当前模型状态信息"""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "cpu_threads": self.cpu_threads if self.device == "cpu" else None,
            "language": self.language,
            "cuda_available": self._is_cuda_available(),
            "gpu_info": self._get_gpu_info() if self.device == "cuda" else None
        }

    def _get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """获取GPU信息，如果可用"""
        try:
            if torch.cuda.is_available():
                return {
                    "name": torch.cuda.get_device_name(0),
                    "count": torch.cuda.device_count(),
                    "current_device": torch.cuda.current_device(),
                    "memory_allocated": f"{torch.cuda.memory_allocated() / 1024**2:.2f} MB",
                    "memory_reserved": f"{torch.cuda.memory_reserved() / 1024**2:.2f} MB"
                }
        except Exception as e:
            logger.warning(f"获取GPU信息时出错: {e}")
        return None