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

## License / 许可协议

See [`LICENSE`](LICENSE) for the full English text (**MIT License with Anti-Abuse Clause**).

完整英文文本见 [`LICENSE`](LICENSE)（**附带使用限制的 MIT 许可**）。

### 一、开源许可（MIT License）

特此免费授予任何获得本软件副本及相关文档文件（以下简称「本软件」）的人，无限制使用本软件的权利，包括但不限于使用、复制、修改、合并、出版、分发、再许可和/或出售本软件副本，并允许向其提供本软件的人这样做，但须遵守以下条件：

上述版权声明和本许可声明应包含在本软件的所有副本或主要部分中。

### 二、使用限制与禁止行为

1. 本软件仅用于学习、编程练习、单机本地测试。
2. 严禁将本软件用于任何 Minecraft 官方服务器、第三方多人服务器、PVP 对战、排名/竞赛场景，违反者自行承担账号封禁、法律责任等全部后果。
3. 严禁对本软件进行二次开发以实现绕过反作弊、注入游戏进程、修改游戏内存、抓包篡改数据等作弊功能。
4. 严禁以任何形式商用、售卖、收费分发、捐赠变现、引流获利。
5. 严禁移除、修改本软件中的版权声明与许可协议。

### 三、免责声明（核心法律保护）

本软件按「原样」提供，不提供任何明示或暗示的担保，包括但不限于适销性、特定用途适用性和非侵权担保。

在任何情况下，作者或版权持有人均不对任何索赔、损害或其他责任负责，无论是合同、侵权或其他行为，因使用本软件、滥用本软件、在服务器违规使用导致的一切后果，均由使用者独立承担全部责任，作者不承担任何法律与连带责任。

Copyright (c) 2026 WesternYao

## About the English text / 关于英文说明

My English is not strong enough to write the full introduction myself, so the English parts of this README were edited with the help of AI translation.

我的英语能力不足以支撑我编辑整个简介，因此使用了 AI 翻译进行编辑。
