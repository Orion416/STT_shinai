"""
语音转文本系统 - 后端实现
基于Faster Whisper的高性能语音转文本系统，支持文件上传和麦克风实时转写
"""

import os
import tempfile
import numpy as np
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
import moviepy.editor as mp
import ntpath

class SpeechToText:
    """
    语音转文字核心类，封装了音频处理、转写和视频提取等功能
    """
    def __init__(self, model_size="medium", force_gpu=True):
        """
        初始化语音转文字转换器

        Args:
            model_size (str): Whisper模型大小，可选值: "tiny", "base", "small", "medium", "large"
            force_gpu (bool): 是否强制使用GPU加速（如果可用）
        """
        # 音频录制默认参数
        self.sample_rate = 16000  # 采样率：16kHz
        self.channels = 1         # 单声道
        self.model_size = model_size

        print(f"正在加载Faster Whisper模型: {model_size}")

        # 检查GPU可用性
        cuda_available = self.is_cuda_available()

        # 根据GPU可用性选择设备和计算精度
        if cuda_available and force_gpu:
            device = "cuda"
            compute_type = "float16"  # 使用半精度浮点数以节省显存
            print("检测到CUDA GPU，优先使用GPU加速处理")

            # 尝试使用GPU加载模型
            try:
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
                print(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")
                return
            except Exception as e:
                print(f"GPU加载失败，错误信息: {e}")
                print("尝试改用CPU...")

        # CPU作为备选方案
        device = "cpu"
        compute_type = "int8"  # 使用8位整数计算以节省内存
        if cuda_available:
            print("CUDA GPU可用，但使用CPU处理（可能是GPU初始化失败）")
        else:
            print("使用CPU进行处理")

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"模型加载成功：使用{device.upper()}，计算精度为{compute_type}")

    def is_cuda_available(self):
        """
        检查系统是否支持CUDA GPU加速，使用更可靠的检测方式

        Returns:
            bool: 如果CUDA可用返回True，否则返回False
        """
        try:
            import torch
            # 基本检查
            if not torch.cuda.is_available():
                print("PyTorch报告CUDA不可用")
                return False

            # 进一步测试，创建一个小张量
            try:
                test_tensor = torch.zeros(1).cuda()
                test_tensor = test_tensor + 1  # 执行简单操作检验GPU是否正常工作
                test_tensor.cpu()  # 释放GPU内存
                print("CUDA测试成功，GPU工作正常")
                return True
            except Exception as e:
                print(f"CUDA测试失败: {e}")
                return False
        except ImportError:
            print("未安装PyTorch，无法使用GPU")
            return False
        except Exception as e:
            print(f"检查CUDA时出错: {e}")
            return False

    def get_status(self):
        """
        获取STT引擎状态信息

        Returns:
            dict: 包含模型大小等信息的字典
        """
        return {
            "model_size": self.model_size,
            "ready": True
        }

    def get_available_models(self):
        """
        获取可用的模型列表

        Returns:
            list: 可用模型列表
        """
        return ["tiny", "base", "small", "medium", "large-v1", "large-v2", "large-v3"]

    def record_audio(self, duration=5):
        """
        使用麦克风录制音频

        Args:
            duration (int): 录制时长（秒）

        Returns:
            numpy.ndarray: 录制的音频数据
        """
        print(f"开始录制音频，时长{duration}秒...")
        audio_data = sd.rec(
            int(self.sample_rate * duration),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='float32'
        )
        sd.wait()  # 等待录制完成
        print("录制完成")
        return audio_data

    def save_audio_to_file(self, audio_data, filename="recording.wav"):
        """
        将音频数据保存为WAV文件

        Args:
            audio_data (numpy.ndarray): 要保存的音频数据
            filename (str): 保存的文件名

        Returns:
            str: 保存的文件路径
        """
        sf.write(filename, audio_data, self.sample_rate)
        return filename

    def is_video_file(self, file_path):
        """
        检查文件是否为视频文件

        Args:
            file_path (str): 文件路径

        Returns:
            bool: 如果是视频文件返回True，否则返回False
        """
        # 获取文件扩展名并转换为小写
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        # 支持的视频文件扩展名列表
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

        return ext in video_extensions

    def extract_audio_from_video(self, video_file):
        """
        从视频文件中提取音频

        Args:
            video_file (str): 视频文件路径

        Returns:
            str: 提取出的音频文件路径

        Raises:
            Exception: 如果音频提取失败
        """
        print(f"正在从视频文件中提取音频: {video_file}")

        # 在临时目录创建音频文件
        temp_dir = tempfile.gettempdir()
        video_filename = ntpath.basename(video_file)
        audio_file = os.path.join(temp_dir, f"{os.path.splitext(video_filename)[0]}_audio.wav")

        # 使用moviepy提取音频
        try:
            video = mp.VideoFileClip(video_file)
            video.audio.write_audiofile(audio_file, logger=None)
            print(f"音频已提取到: {audio_file}")
            return audio_file
        except Exception as e:
            print(f"从视频提取音频失败: {e}")
            raise

    def transcribe(self, audio_file, language=None):
        """
        将音频文件转换为文字

        Args:
            audio_file (str): 音频文件路径
            language (str, optional): 语言代码，如'zh'表示中文

        Returns:
            tuple: (转写文本, 详细信息字典)
        """
        print(f"开始转写文件: {audio_file}")

        # 如果是视频文件，先提取音频
        if self.is_video_file(audio_file):
            print("检测到视频文件，正在提取音频...")
            audio_file = self.extract_audio_from_video(audio_file)

        print(f"处理音频文件: {audio_file}")
        # 使用Whisper模型进行转写
        segments, info = self.model.transcribe(audio_file, beam_size=5, language=language)

        # 合并所有片段得到完整转写结果
        transcription = " ".join([segment.text for segment in segments])

        # 构建详细信息
        details = {
            "language": info.language,
            "language_probability": float(info.language_probability),
            "duration": info.duration,
            "segments_count": len(list(segments))
        }

        print(f"检测到语言: {info.language}，置信度: {info.language_probability:.2f}")

        # 清理临时音频文件
        if "_audio.wav" in audio_file and tempfile.gettempdir() in audio_file:
            try:
                os.remove(audio_file)
                print(f"已删除临时音频文件: {audio_file}")
            except OSError:
                pass

        return transcription, details

    def transcribe_from_microphone(self, duration=5):
        """
        录制麦克风音频并转写为文字

        Args:
            duration (int): 录制时长（秒）

        Returns:
            str: 转写后的文字内容
        """
        # 录制音频
        audio_data = self.record_audio(duration)

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            temp_filename = tmp_file.name

        self.save_audio_to_file(audio_data, temp_filename)

        # 转写音频
        transcription, _ = self.transcribe(temp_filename)

        # 清理临时文件
        os.remove(temp_filename)

        return transcription

def main():
    print("Speech-to-Text with Faster Whisper")
    print("==================================")

    # 初始化语音转文字转换器
    model_size = input("选择模型大小 (tiny, base, small, medium, large) [默认: medium]: ").strip() or "medium"

    # 询问用户是否强制使用GPU
    use_gpu = input("是否优先使用GPU加速? (y/n) [默认: y]: ").strip().lower() or "y"
    force_gpu = use_gpu == "y"

    stt = SpeechToText(model_size=model_size, force_gpu=force_gpu)

    while True:
        print("\nOptions:")
        print("1. Record and transcribe from microphone")
        print("2. Transcribe from audio/video file")
        print("3. Exit")

        choice = input("Enter your choice (1-3): ").strip()

        if choice == "1":
            try:
                duration = int(input("Enter recording duration in seconds [default: 5]: ").strip() or "5")
                print("\nStarting recording. Speak now...")
                transcription = stt.transcribe_from_microphone(duration)
                print("\nTranscription:")
                print(transcription)
            except Exception as e:
                print(f"Error during recording/transcription: {e}")

        elif choice == "2":
            try:
                audio_file = input("Enter path to audio/video file: ").strip()
                if os.path.exists(audio_file):
                    transcription, details = stt.transcribe(audio_file)
                    print("\nTranscription:")
                    print(transcription)
                else:
                    print(f"File not found: {audio_file}")
            except Exception as e:
                print(f"Error during transcription: {e}")

        elif choice == "3":
            print("Exiting...")
            break

        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--api":
        # Run as API server
        from flask import Flask, request, jsonify
        from flask_cors import CORS
        import base64
        import io
        import argparse

        # 解析命令行参数
        parser = argparse.ArgumentParser(description="语音转文本 API服务器")
        parser.add_argument('--api', action='store_true', help="以API服务器模式运行")
        parser.add_argument('--model', default='medium', choices=['tiny', 'base', 'small', 'medium', 'large'],
                            help="Whisper模型大小 (默认: medium)")
        parser.add_argument('--force_gpu', default='True', choices=['True', 'False'],
                            help="是否强制使用GPU (默认: True)")
        parser.add_argument('--port', type=int, default=5005, help="API服务器端口 (默认: 5005)")
        parser.add_argument('--host', default='0.0.0.0', help="API服务器监听地址 (默认: 0.0.0.0)")

        args = parser.parse_args()

        app = Flask(__name__)
        CORS(app)  # 启用CORS以允许跨域请求

        # 设置最大请求大小为100MB
        app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

        # 初始化STT模型
        print(f"Initializing STT model for API with {args.model} model, force_gpu={args.force_gpu}...")
        force_gpu = args.force_gpu.lower() == 'true'
        stt = SpeechToText(model_size=args.model, force_gpu=force_gpu)

        @app.route('/api/health', methods=['GET'])
        def health_check():
            """健康检查端点"""
            return jsonify({
                "status": "ok",
                "message": "服务正常",
                "engine_status": stt.get_status()
            })

        @app.route('/api/models', methods=['GET'])
        def get_models():
            """获取可用模型列表"""
            return jsonify({
                "available_models": stt.get_available_models(),
                "current_model": stt.model_size
            })

        @app.route('/api/transcribe', methods=['POST'])
        def transcribe_api():
            print("\n\n======== 接收到新的文件上传请求 ========")
            # 打印请求信息
            print(f"请求方法: {request.method}")
            print(f"请求头: {request.headers}")
            print(f"请求文件: {request.files.keys()}")

            if 'file' not in request.files:
                print("错误：请求中没有文件")
                return jsonify({'error': 'No file part'}), 400

            file = request.files['file']
            if file.filename == '':
                print("错误：没有选择文件")
                return jsonify({'error': 'No selected file'}), 400

            print(f"接收到文件: {file.filename}, 大小: {file.content_length if hasattr(file, 'content_length') else '未知'} 字节")

            # 保存上传的文件
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, file.filename)
            try:
                file.save(temp_path)
                file_size = os.path.getsize(temp_path)
                print(f"文件已保存到临时路径: {temp_path}, 文件大小: {file_size} 字节")
            except Exception as e:
                print(f"保存文件时出错: {str(e)}")
                return jsonify({'success': False, 'error': f"保存文件失败: {str(e)}"}), 500

            try:
                # 检查文件是否存在并可访问
                if not os.path.exists(temp_path):
                    print(f"错误：保存的文件不存在: {temp_path}")
                    return jsonify({'success': False, 'error': "保存的文件不存在"}), 500

                # 获取语言参数
                language = request.form.get('language')

                # 转写音频
                print(f"开始转写文件: {file.filename}")
                # 设置超时时间，防止处理大文件时卡住
                transcription, details = stt.transcribe(temp_path, language=language)
                print(f"转写完成，文本长度: {len(transcription)}")
                print(f"转写结果前100字符: {transcription[:100]}..." if len(transcription) > 100 else f"转写结果: {transcription}")

                # 清理临时文件
                try:
                    os.remove(temp_path)
                    print(f"临时文件已删除: {temp_path}")
                except Exception as e:
                    print(f"删除临时文件时出错: {str(e)}")

                return jsonify({
                    'success': True,
                    'transcription': transcription,
                    'details': details
                })
            except Exception as e:
                print(f"转写过程出错: {str(e)}")
                import traceback
                traceback.print_exc()

                # 尝试清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        print(f"临时文件已删除: {temp_path}")
                except:
                    pass

                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @app.route('/api/transcribe-blob', methods=['POST'])
        def transcribe_blob():
            print("\n\n======== 接收到新的音频数据 ========")

            if 'audio' not in request.files:
                print("错误：请求中没有音频数据")
                return jsonify({'error': 'No audio data received'}), 400

            file = request.files['audio']
            print(f"接收到音频数据, 大小: {request.content_length if hasattr(request, 'content_length') else '未知'} 字节")

            # 保存上传的音频数据
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "recorded_audio.wav")

            try:
                file.save(temp_path)
                file_size = os.path.getsize(temp_path)
                print(f"音频已保存到临时路径: {temp_path}, 文件大小: {file_size} 字节")
            except Exception as e:
                print(f"保存音频时出错: {str(e)}")
                return jsonify({'success': False, 'error': f"保存音频失败: {str(e)}"}), 500

            try:
                # 检查文件是否存在并可访问
                if not os.path.exists(temp_path):
                    print(f"错误：保存的音频文件不存在: {temp_path}")
                    return jsonify({'success': False, 'error': "保存的音频文件不存在"}), 500

                # 获取语言参数
                language = request.form.get('language')

                # 转写音频
                print(f"开始转写音频文件")
                transcription, details = stt.transcribe(temp_path, language=language)
                print(f"转写完成，文本长度: {len(transcription)}")
                print(f"转写结果前100字符: {transcription[:100]}..." if len(transcription) > 100 else f"转写结果: {transcription}")

                # 清理临时文件已经在transcribe方法中完成

                return jsonify({
                    'success': True,
                    'transcription': transcription,
                    'details': details
                })
            except Exception as e:
                print(f"转写过程出错: {str(e)}")
                import traceback
                traceback.print_exc()

                # 尝试清理临时文件
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        print(f"临时文件已删除: {temp_path}")
                except:
                    pass

                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        print(f"Starting API server on {args.host}:{args.port}...")
        app.run(host=args.host, port=args.port, debug=False)
    else:
        # Run as CLI application
        main()
