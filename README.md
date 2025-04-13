# ScreenshotApp

An application for taking screenshots with Gemini AI integration. Allows you to select a screen area, send it to AI, and receive a text analysis.

## Installation

1. Ensure you have Python 3.8+ installed.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```

## Building to .exe

To build the executable, use PyInstaller:
```bash
pyinstaller --onefile --windowed --add-data "ai.png;." main.py
```

## Usage

- Press `Alt + Print Screen` to select a screenshot area.
- Enter a prompt for AI in the pop-up window.
- The result will open in your browser.

## Dependencies

- `keyboard`
- `pyautogui`
- `Pillow`
- `pystray`
- `google-generativeai`