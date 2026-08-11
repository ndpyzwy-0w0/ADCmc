# ADCmc

A controllable Windows auto-clicker with dual left/right channels, speed curves, random timing jitter, hotkey and double-click triggers, DPI-aware UI, and local settings persistence. **For learning and research purposes only.**

可控的 Windows 连点器：左右键双通道、速度曲线、随机时间偏移、热键/双击触发、DPI 自适应界面、本地设置记忆。**仅供学习研究使用。**

## Features / 功能

| Feature | 说明 |
| --- | --- |
| Left / Right panels | 左右键独立连点板块，并排显示 |
| Speed curves | 恒定 / 加速 / 减速 / 正弦 / 缓入缓出 / 自定义曲线 |
| Random jitter | 可开关的随机时间偏移 |
| Bind-key trigger | 录制键盘或鼠标侧键，按住连点 |
| Double-click trigger | 双击间隔小于阈值开始；阈值内无继续输入则停止 |
| DPI-aware UI | 适配高分屏与系统缩放，窗口可调整大小并滚动 |
| Settings file | 同目录 `ADCmc_settings.txt` 记住设置 |

## Requirements / 环境

- Windows 10/11
- Python 3.12+（开发运行）
- 依赖见 `requirements.txt`（`pynput`、打包用 `pyinstaller`）

## Run from source / 源码运行

```powershell
cd ADCmc
python -m pip install -r requirements.txt
python main.py
```

## Build exe / 打包

```powershell
.\build.ps1
```

生成文件：`dist\ADCmc.exe`

## Notes / 说明

- Closing the app saves settings next to the executable / script.
- If `ADCmc_settings.txt` is deleted, defaults are restored and a new file is created.
- 关闭软件时会保存设置；删除配置文件后下次启动恢复默认并重新生成。

## Disclaimer / 免责声明

This project is intended **for learning and research purposes only**. Use responsibly and in compliance with applicable laws and the terms of any software or game you interact with.

本项目**仅供学习研究使用**。请合法、合规、负责任地使用。

## About the English text / 关于英文说明

My English is not strong enough to write the full introduction myself, so the English parts of this README were edited with the help of AI translation.

我的英语能力不足以支撑我编辑整个简介，因此使用了 AI 翻译进行编辑。
