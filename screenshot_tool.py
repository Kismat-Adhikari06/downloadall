import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import time
import pyautogui
import pygetwindow as gw
import keyboard

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")

# Configurable delays (seconds)
DELAY_AFTER_RIGHT_CLICK   = 0.6   # wait for context menu to appear
DELAY_AFTER_SAVE_AS_CLICK = 1.2   # wait for Save dialog to open
DELAY_AFTER_SAVE          = 0.8   # wait after confirming save
DELAY_NEXT_PAGE_CLICK     = 1.0   # wait after clicking next page


def ensure_screenshots_dir():
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


def type_path_in_dialog(filepath: str) -> bool:
    """
    Find the Windows Save dialog, clear the filename field,
    type the full path, and press Enter to confirm.
    Returns True on success.
    """
    deadline = time.time() + 5  # wait up to 5 seconds for dialog
    dialog = None

    while time.time() < deadline:
        for title in ("Save As", "Save Image As", "Save Picture As", "另存为", "名前を付けて保存"):
            wins = gw.getWindowsWithTitle(title)
            if wins:
                dialog = wins[0]
                break
        if dialog:
            break
        time.sleep(0.2)

    if not dialog:
        # Fallback: just type the path and hope the filename field is focused
        keyboard.press_and_release("ctrl+a")
        time.sleep(0.1)
        keyboard.write(filepath, delay=0.02)
        keyboard.press_and_release("enter")
        return True

    dialog.activate()
    time.sleep(0.3)

    # Focus the filename field via Alt+N (standard Windows shortcut)
    keyboard.press_and_release("alt+n")
    time.sleep(0.2)
    keyboard.press_and_release("ctrl+a")
    time.sleep(0.1)
    keyboard.write(filepath, delay=0.02)
    keyboard.press_and_release("enter")
    return True


def save_image_as(center_x: int, center_y: int, filepath: str):
    """Right-click the image, choose Save image as, fill in the path."""
    # Right-click the centre of the screen
    pyautogui.moveTo(center_x, center_y, duration=0.2)
    pyautogui.rightClick()
    time.sleep(DELAY_AFTER_RIGHT_CLICK)

    # "Save image as" is typically the first or second item — use keyboard shortcut
    # 'v' is the underlined letter in "Save image as" in Chrome/Edge
    keyboard.press_and_release("v")
    time.sleep(DELAY_AFTER_SAVE_AS_CLICK)

    # Fill in the Save dialog
    type_path_in_dialog(filepath)
    time.sleep(DELAY_AFTER_SAVE)

    # Dismiss any "file already exists" overwrite prompt
    keyboard.press_and_release("enter")
    time.sleep(0.3)


def run_capture(count: int, status_var: tk.StringVar, start_btn: ttk.Button, root: tk.Tk):
    ensure_screenshots_dir()

    screen_width, screen_height = pyautogui.size()
    center_x  = screen_width  // 2
    center_y  = screen_height // 2
    next_x    = int(screen_width * 0.85)
    next_y    = screen_height // 2

    for i in range(1, count + 1):
        status_var.set(f"Saving image {i} of {count}...")
        root.update_idletasks()

        filename  = f"{i:03d}.png"
        filepath  = os.path.join(SCREENSHOTS_DIR, filename)

        save_image_as(center_x, center_y, filepath)

        if i < count:
            status_var.set(f"Saved {i} of {count} — going to next page...")
            root.update_idletasks()
            pyautogui.moveTo(next_x, next_y, duration=0.2)
            pyautogui.click()
            time.sleep(DELAY_NEXT_PAGE_CLICK)

    status_var.set(f"Done! {count} image(s) saved.")
    start_btn.config(state="normal")


def start_capture(count_var: tk.StringVar, status_var: tk.StringVar,
                  start_btn: ttk.Button, root: tk.Tk):
    raw = count_var.get().strip()
    if not raw.isdigit() or int(raw) < 1:
        messagebox.showerror("Invalid input", "Please enter a positive integer.")
        return

    count = int(raw)
    start_btn.config(state="disabled")
    status_var.set("Starting in 3 seconds — switch to your browser!")
    root.update_idletasks()
    time.sleep(3)

    thread = threading.Thread(target=run_capture,
                              args=(count, status_var, start_btn, root),
                              daemon=True)
    thread.start()


def build_ui():
    root = tk.Tk()
    root.title("Image Saver")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.92)
    root.wm_attributes("-topmost", True)

    pad = {"padx": 10, "pady": 6}

    frame = ttk.Frame(root, padding=12)
    frame.grid(row=0, column=0, sticky="nsew")

    ttk.Label(frame, text="Images to save:").grid(row=0, column=0, sticky="w", **pad)

    count_var = tk.StringVar(value="5")
    ttk.Entry(frame, textvariable=count_var, width=8, justify="center").grid(
        row=0, column=1, sticky="w", **pad)

    status_var = tk.StringVar(value="Ready")
    ttk.Label(frame, textvariable=status_var, foreground="gray",
              width=36, anchor="w").grid(row=1, column=0, columnspan=2, sticky="w", **pad)

    start_btn = ttk.Button(frame, text="Start",
                           command=lambda: start_capture(count_var, status_var, start_btn, root))
    start_btn.grid(row=2, column=0, columnspan=2, sticky="ew", **pad)

    def keep_on_top():
        root.attributes("-topmost", True)
        root.after(500, keep_on_top)

    keep_on_top()
    root.mainloop()


if __name__ == "__main__":
    build_ui()
