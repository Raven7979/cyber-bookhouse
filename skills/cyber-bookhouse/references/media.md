# 本地视频与音频

用户提供本地文件时，使用包内脚本取得时长、媒体信息、代表帧和本地逐字稿。
第一次处理前同时读取 [runtime-models.md](runtime-models.md)，并用一张实际
代表帧验收当前模型/入口的图片识别能力。

先检查能力：

```bash
<python-command> "<skill-dir>/scripts/dependency_doctor.py" --require media
<python-command> "<skill-dir>/scripts/dependency_doctor.py" --require local_asr
```

只抽取代表帧：

```bash
<python-command> "<skill-dir>/scripts/media_capture.py" "<path-to-video>" \
  --frames 6 \
  --output-dir "<vault>/链接采集/_assets/<capture-id>"
```

代表帧和本地转写：

```bash
<python-command> "<skill-dir>/scripts/media_capture.py" "<path-to-video>" \
  --frames 6 --transcribe --language zh \
  --output-dir "<vault>/链接采集/_assets/<capture-id>"
```

- 转写在本机执行，不把媒体上传到未说明的第三方服务。
- Windows 使用 OpenAI Whisper；MLX Whisper 只用于 Apple silicon。
- 首次使用高质量转写模型可能会下载模型文件；执行前告诉用户。
- 机器转写初稿标记为 `asr_raw`；结合画面、上下文和专有名词校对后，
  才能改为 `asr_proofread`。
- “蒸馏笔记”的镜头结论必须由实际画面支持。只有逐字稿时，只分析语言结构。
- 模型不需要原生接收 MP4；代表帧识别和本地转写共同组成视频理解证据。
