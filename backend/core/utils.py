"""语音转文本工具函数模块
处理音频和视频文件的转换、处理和检查
"""

import os
import logging
import tempfile
import subprocess
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

# 配置日志
logger = logging.getLogger("STT_Utils")

# 支持的视频格式
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']

def check_ffmpeg_available() -> bool:
    """
    检查系统是否安装了FFmpeg

    Returns:
        bool: FFmpeg是否可用
    """
    try:
        subprocess.run(
            ['ffmpeg', '-version'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.warning("FFmpeg未安装或不可用。处理视频文件需要FFmpeg。")
        return False


def convert_video_to_audio(video_path: str, output_format: str = 'wav') -> Tuple[str, bool]:
    """
    将视频文件转换为音频文件

    Args:
        video_path: 视频文件路径
        output_format: 输出音频格式，默认为wav

    Returns:
        Tuple[str, bool]: (输出音频路径, 是否成功)
    """
    if not check_ffmpeg_available():
        logger.error("未检测到FFmpeg，无法处理视频文件")
        return "", False

    # 创建临时音频文件
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as tmp:
            audio_path = tmp.name

        logger.info(f"正在将视频转换为音频: {video_path} -> {audio_path}")

        # 使用FFmpeg转换视频到音频
        result = subprocess.run(
            [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # 不处理视频
                '-ar', '16000',  # 采样率16kHz
                '-ac', '1',  # 单声道
                '-y',  # 覆盖已存在的文件
                audio_path
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
            logger.info(f"视频转换成功: {os.path.getsize(audio_path) / 1024:.1f} KB")
            return audio_path, True
        else:
            logger.error("视频转换失败: 输出文件为空")
            return "", False

    except subprocess.SubprocessError as e:
        logger.error(f"视频转换失败: {str(e)}")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return "", False
    except Exception as e:
        logger.error(f"视频转换过程出错: {str(e)}")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return "", False


def normalize_audio(audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    规范化音频数据

    Args:
        audio_data: 音频数据
        sample_rate: 采样率

    Returns:
        规范化的音频数据
    """
    # 降采样至16kHz (如果需要)
    if sample_rate != 16000:
        # 这里使用简单的重采样方法，实际中可以使用librosa等库进行更高质量的重采样
        ratio = 16000 / sample_rate
        audio_data = np.interp(
            np.arange(0, len(audio_data) * ratio, ratio),
            np.arange(0, len(audio_data)),
            audio_data
        )

    # 归一化音量
    if np.max(np.abs(audio_data)) > 0:
        audio_data = audio_data / np.max(np.abs(audio_data))

    return audio_data


def read_audio_file(file_path: str) -> Tuple[np.ndarray, int]:
    """
    读取音频文件

    Args:
        file_path: 音频文件路径

    Returns:
        Tuple[np.ndarray, int]: (音频数据, 采样率)
    """
    try:
        # 使用soundfile读取音频文件
        audio_data, sample_rate = sf.read(file_path)

        # 如果是立体声，转换为单声道
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            audio_data = audio_data.mean(axis=1)

        # 规范化音频
        audio_data = normalize_audio(audio_data, sample_rate)

        return audio_data, 16000

    except Exception as e:
        logger.error(f"读取音频文件失败: {str(e)}")
        raise


def is_video_file(file_path: str) -> bool:
    """
    检查文件是否为视频文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为视频文件
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower() in SUPPORTED_VIDEO_FORMATS


def is_audio_file(file_path: str) -> bool:
    """
    检查文件是否为音频文件

    Args:
        file_path: 文件路径

    Returns:
        bool: 是否为音频文件
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower() in ['.wav', '.mp3', '.flac', '.ogg', '.m4a']


def cleanup_temp_files(file_list: List[str]) -> None:
    """
    清理临时文件

    Args:
        file_list: 要删除的文件路径列表
    """
    for file_path in file_list:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                logger.debug(f"已删除临时文件: {file_path}")
            except Exception as e:
                logger.warning(f"无法删除临时文件 {file_path}: {str(e)}")


def get_available_whisper_models() -> List[str]:
    """
    获取可用的Whisper模型列表

    Returns:
        List[str]: 模型名称列表
    """
    return [
        "tiny", "base", "small", "medium",
        "large-v1", "large-v2", "large-v3"
    ]