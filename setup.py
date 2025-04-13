from cx_Freeze import setup, Executable

setup(
    name="ScreenshotApp",
    version="1.0",
    description="Приложение для скриншотов с AI",
    executables=[Executable("main.py", base="Win32GUI")],
    options={
        "build_exe": {
            "include_files": ["ai.png"], 
        }
    }
)