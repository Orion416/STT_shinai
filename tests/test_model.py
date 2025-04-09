#!/usr/bin/env python3
"""
测试 Faster Whisper 模型是否正常工作
此脚本会下载一个示例音频并对其进行转录
"""

import os
import urllib.request
import sys

from faster_whisper import WhisperModel

def download_test_audio():
    """下载测试用的音频文件"""
    test_audio_url = "https://github.com/openai/whisper/raw/main/tests/jfk.flac"
    test_audio_path = "test_audio.flac"
    
    if not os.path.exists(test_audio_path):
        print(f"下载测试音频文件: {test_audio_url}")
        urllib.request.urlretrieve(test_audio_url, test_audio_path)
        print(f"音频文件已保存到: {test_audio_path}")
    else:
        print(f"使用已存在的测试文件: {test_audio_path}")
    
    return test_audio_path

def test_whisper_model(model_size="medium", force_gpu=True):
    """测试 Whisper 模型转录能力"""
    print(f"加载 Faster Whisper 模型 ({model_size})...")
    
    # 检查是否可以使用 GPU
    cuda_available = is_cuda_available()
    
    # 决定使用哪个设备
    if cuda_available and force_gpu:
        device = "cuda"
        compute_type = "float16"
        print("CUDA GPU可用，优先使用GPU加速处理")
        
        # 尝试使用GPU加载模型
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")
        except Exception as e:
            print(f"GPU加载失败，错误信息: {e}")
            print("尝试改用CPU...")
            device = "cpu"
            compute_type = "int8"
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")
    else:
        # 使用CPU作为备选
        device = "cpu"
        compute_type = "int8"
        if cuda_available:
            print("CUDA GPU可用，但使用CPU处理（未强制使用GPU）")
        else:
            print("使用CPU进行处理")
            
        try:
            model = WhisperModel(model_size, device=device, compute_type=compute_type)
            print(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")
        except Exception as e:
            print(f"模型加载失败: {e}")
            sys.exit(1)
    
    # 下载并转录测试音频
    test_audio = download_test_audio()
    
    print(f"开始转录音频...")
    segments, info = model.transcribe(test_audio, beam_size=5)
    
    print("\n转录结果:")
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    
    print(f"\n检测到的语言: {info.language} (概率: {info.language_probability:.2f})")
    print("\n转录测试完成！")

def is_cuda_available():
    """检查是否可以使用 CUDA"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

if __name__ == "__main__":
    # 从命令行参数获取模型大小，默认为 medium
    model_size = sys.argv[1] if len(sys.argv) > 1 else "medium"
    valid_sizes = ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3", "large"]
    
    if model_size not in valid_sizes:
        print(f"无效的模型大小: {model_size}")
        print(f"有效选项: {', '.join(valid_sizes)}")
        sys.exit(1)
    
    # 是否强制使用GPU
    if len(sys.argv) > 2:
        force_gpu = sys.argv[2].lower() in ["true", "yes", "y", "1"]
    else:
        force_gpu = True
    
    test_whisper_model(model_size, force_gpu) 