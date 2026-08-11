# ADCmc

[English](README.md) | [中文](README.zh-CN.md)

A controllable Windows auto-clicker with dual left/right channels, speed curves, random timing jitter, hotkey and double-click triggers, DPI-aware UI, and local settings persistence. **For learning and research purposes only.**

## Features

| Feature | Description |
| --- | --- |
| Left / Right panels | Independent left- and right-click panels, side by side |
| Speed curves | Constant / accelerate / decelerate / sine / ease / custom |
| Random jitter | Optional random timing offset between clicks |
| Bind-key trigger | Record a keyboard or mouse side button; hold to click |
| Double-click trigger | Start when two clicks fall within a threshold; stop if input stops |
| DPI-aware UI | Scales with display DPI; resizable window with scrolling |
| Settings file | Saves preferences to `ADCmc_settings.txt` next to the app |

## Requirements

- Windows 10/11
- Python 3.12+ (for running from source)
- See `requirements.txt` (`pynput`; `pyinstaller` for packaging)

## Run from source

```powershell
cd ADCmc
python -m pip install -r requirements.txt
python main.py
```

## Build exe

```powershell
.\build.ps1
```

Output: `dist\ADCmc.exe`

## Notes

- Closing the app saves settings next to the executable or script.
- If `ADCmc_settings.txt` is deleted, defaults are restored and a new file is created.

## License

This project is licensed under the [MIT License](LICENSE).

Copyright (c) 2026 WesYao

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. See [LICENSE](LICENSE) for the full text.

## About the English text

My English is not strong enough to write the full introduction myself, so the English parts of this documentation were edited with the help of AI translation.
