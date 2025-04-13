import keyboard
import pyautogui
import os
import tkinter as tk
from tkinter import Label, Frame, Entry
from PIL import Image, ImageTk, ImageGrab
import tempfile
from datetime import datetime
import threading
import webbrowser
from google import genai
import pystray

try:
    import markdown
    md_enabled = True
except ImportError:
    md_enabled = False

API_KEY = "AIzaSyD92YU9s5VAdCtj4vzlhTI2ARYu0SywdKk"
client = genai.Client(api_key=API_KEY)


class ScreenshotApp:
    def __init__(self):
        self.screenshot_path = None
        self.is_listening = True
        self.selection_coords = None
        self.root = tk.Tk()
        self.root.withdraw()  
        self.setup_tray_icon()  
        self.setup_hotkey_listener()

    def setup_tray_icon(self):
        image = Image.open("./ai.png")
        menu = pystray.Menu(
            pystray.MenuItem("Выход", self.on_exit)
        )
        self.tray_icon = pystray.Icon(
            "ScreenshotApp",
            icon=image,
            title="Screenshot App",
            menu=menu
        )
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_exit(self):
        self.tray_icon.stop() 
        self.root.quit() 

    def setup_hotkey_listener(self):
        listener_thread = threading.Thread(target=self.listen_for_hotkey, daemon=True)
        listener_thread.start()

    def listen_for_hotkey(self):
        keyboard.add_hotkey('alt+print_screen', self.start_area_selection)
        keyboard.wait()

    def start_area_selection(self):
        if not self.is_listening:
            return

        self.is_listening = False
        temp_screenshot = pyautogui.screenshot()

        self.selection_window = tk.Toplevel(self.root)
        self.selection_window.attributes('-fullscreen', True)
        self.selection_window.attributes('-topmost', True)

        self.bg_image = ImageTk.PhotoImage(temp_screenshot)

        self.canvas = tk.Canvas(self.selection_window, cursor="cross",
                                width=self.root.winfo_screenwidth(),
                                height=self.root.winfo_screenheight())
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, image=self.bg_image, anchor=tk.NW)
        self.canvas.create_text(self.root.winfo_screenwidth() // 2, 30,
                                text="Выделите область для скриншота",
                                fill="white", font=("Arial", 16))

        self.canvas.bind("<ButtonPress-1>", self.on_selection_start)
        self.canvas.bind("<B1-Motion>", self.on_selection_motion)
        self.canvas.bind("<ButtonRelease-1>", self.on_selection_release)

        self.selection_window.bind("<Escape>", self.on_selection_cancel)
        self.start_x = self.start_y = self.rect_id = None

    def on_selection_start(self, event):
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y,
                                                    self.start_x + 1, self.start_y + 1,
                                                    outline='red', width=2)

    def on_selection_motion(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)

    def on_selection_release(self, event):
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        self.selection_coords = (
            min(self.start_x, end_x),
            min(self.start_y, end_y),
            max(self.start_x, end_x),
            max(self.start_y, end_y)
        )
        self.selection_window.destroy()
        self.take_screenshot_of_area()

    def on_selection_cancel(self, event):
        self.selection_window.destroy()
        self.is_listening = True

    def take_screenshot_of_area(self):
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_path = os.path.join(temp_dir, f"screenshot_area_{timestamp}.png")
        x1, y1, x2, y2 = self.selection_coords
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        screenshot.save(self.screenshot_path)
        self.screenshot = screenshot
        self.show_prompt_window()

    def show_prompt_window(self):
        self.prompt_window = tk.Toplevel(self.root)
        self.prompt_window.title("Введите промт для AI")
        self.prompt_window.geometry("500x150") 
        self.prompt_window.minsize(400, 150)   
        self.prompt_window.attributes('-topmost', True)
        self.prompt_window.config(bg="white")

        prompt_frame = Frame(self.prompt_window, bg="white")
        prompt_frame.pack(fill=tk.BOTH, padx=20, pady=10, expand=True)

        prompt_label = Label(prompt_frame, text="Введите промт для AI:", bg="white", font=("Helvetica", 14))
        prompt_label.pack(anchor=tk.W, pady=(0, 10))

        prompt_entry = Entry(
            prompt_frame,
            bg="white",
            fg="black",
            font=("Helvetica", 14),
            bd=2,
            relief="groove",
            width=40
        )
        prompt_entry.pack(fill=tk.X, pady=(0, 10))
        prompt_entry.focus_set()

        submit_button = tk.Button(
            prompt_frame,
            text="Отправить",
            command=lambda: process_prompt(),
            font=("Helvetica", 12),
            bg="#4a6baf",
            fg="white",
            relief="flat",
            padx=10,
            pady=5
        )
        submit_button.pack(pady=(5, 0))

        def process_prompt(event=None):
            user_prompt = prompt_entry.get().strip()
            if user_prompt:
                self.prompt_window.destroy()
                self.analyze_with_ai(user_prompt)

        prompt_entry.bind('<Return>', process_prompt)
        self.prompt_window.protocol("WM_DELETE_WINDOW", lambda: self.on_prompt_window_close(self.prompt_window))

    def on_prompt_window_close(self, window):
        window.destroy()
        self.is_listening = True

    def analyze_with_ai(self, prompt):
        try:
            prompt_with_language = f"{prompt}\n\nОтветь на русском языке."
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[self.screenshot, prompt_with_language]
            )
            result = response.text
            if os.path.exists(self.screenshot_path):
                os.remove(self.screenshot_path)
            self.show_result_in_browser(result)
        except Exception as e:
            self.show_error_window(str(e))

    def show_result_in_browser(self, markdown_text):
        if md_enabled:
            html_content = markdown.markdown(markdown_text)
        else:
            html_content = f"<pre>{markdown_text}</pre>"

        html_page = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Результат анализа</title>
            <style>
                body {{
                    font-family: 'Helvetica', sans-serif;
                    background: linear-gradient(135deg, #f5f7fa, #e4e8f0);
                    padding: 0;
                    margin: 0;
                    min-height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }}
                .container {{
                    max-width: 900px;
                    width: 90%;
                    margin: 20px auto;
                    background: #fff;
                    padding: 30px;
                    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                    border-radius: 12px;
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    color: #4a6baf;
                    font-size: 28px;
                    margin-bottom: 10px;
                }}
                .header p {{
                    color: #666;
                    font-size: 16px;
                }}
                pre {{
                    background-color: #2d2d2d;
                    color: #f8f8f2;
                    padding: 20px;
                    border-radius: 8px;
                    overflow-x: auto;
                    font-family: 'JetBrains Mono', monospace;
                    font-size: 14px;
                    line-height: 1.5;
                }}
                code {{
                    font-family: 'JetBrains Mono', monospace;
                    background-color: #eaeaea;
                    padding: 2px 6px;
                    border-radius: 4px;
                    color: #333;
                }}
                a {{
                    color: #4a6baf;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                blockquote {{
                    border-left: 4px solid #4a6baf;
                    padding-left: 15px;
                    margin: 20px 0;
                    color: #555;
                    font-style: italic;
                }}
                .content {{
                    line-height: 1.8;
                }}
                .content p {{
                    margin-bottom: 15px;
                }}
                .content img {{
                    max-width: 100%;
                    border-radius: 8px;
                    margin: 15px 0;
                }}
            </style>
            <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Результат анализа</h1>
                    <p>Сгенерировано с помощью Gemini AI</p>
                </div>
                <div class="content">
                    {html_content}
                </div>
            </div>
        </body>
        </html>
        """
        temp_dir = tempfile.gettempdir()
        html_file_path = os.path.join(temp_dir, "ai_result.html")
        with open(html_file_path, "w", encoding="utf-8") as f:
            f.write(html_page)
        webbrowser.open_new_tab("file://" + html_file_path)
        self.is_listening = True

    def show_error_window(self, error_message):
        error_window = tk.Toplevel(self.root)
        error_window.title("Ошибка")
        error_window.geometry("400x200")
        error_window.attributes('-topmost', True)
        error_window.config(bg="white")

        error_label = Label(error_window, text=f"Произошла ошибка:\n{error_message}",
                            wraplength=350, justify=tk.LEFT, bg="white", font=("Helvetica", 12))
        error_label.pack(pady=30, padx=20)

        ok_button = tk.Button(error_window, text="OK", command=error_window.destroy, font=("Helvetica", 12))
        ok_button.pack(pady=10)

        error_window.protocol("WM_DELETE_WINDOW", lambda: self.on_error_window_close(error_window))

    def on_error_window_close(self, window):
        window.destroy()
        self.is_listening = True

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = ScreenshotApp()
    app.run()
