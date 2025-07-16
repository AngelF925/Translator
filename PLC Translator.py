import customtkinter as ctk
from tkinter import filedialog, messagebox
from googletrans import Translator
import threading
import re
import time
import os
import json
from tkinter import Canvas

# App appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
translator = Translator()
cancel_requested = False
batch_size = 5

# Cache setup
CACHE_FILE = os.path.join(os.path.dirname(__file__), "cache.json")
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        translation_cache = json.load(f)
else:
    translation_cache = {}

def save_cache():
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(translation_cache, f, ensure_ascii=False, indent=2)

def clear_cache():
    global translation_cache
    if not os.path.exists(CACHE_FILE):
        messagebox.showinfo("No Cache Found", "No cache file exists to delete.")
        return
    confirm = messagebox.askokcancel(
        "Confirm Delete", "Are you sure you want to delete the saved translation cache?\nThis action cannot be undone."
    )
    if confirm:
        try:
            os.remove(CACHE_FILE)
            translation_cache = {}
            messagebox.showinfo("Cache Cleared", "Translation cache has been deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete cache file:\n{e}")

def cancel_translation():
    global cancel_requested
    cancel_requested = True
    
def smooth_progress_update(current_value, target_value, speed=0.01):
    step = 0.001
    while current_value < target_value:
        current_value = min(current_value + step, target_value)
        width = int(PROGRESS_WIDTH * current_value)
        progress_canvas.coords(bar_fill, 0, 0, width, PROGRESS_HEIGHT)
        progress_canvas.itemconfigure(progress_text, text=f"{round(current_value * 100)}%")
        app.update_idletasks()
        time.sleep(speed)

def translate_file():
    def process_file():
        global cancel_requested
        cancel_requested = False

        input_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if not input_path:
            return

        output_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
        if not output_path:
            return

        # Move this line here — only show 0% after file is chosen
        app.after(0, lambda: progress_canvas.itemconfigure(progress_text, state="normal"))
        app.after(0, lambda: cancel_button.configure(state="normal"))

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(input_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()

        total_lines = len(lines)
        translated_lines = []

        i = 0
        while i < total_lines:
            if cancel_requested:
                def handle_cancel_ui():
                    progress_canvas.coords(bar_fill, 0, 0, 0, PROGRESS_HEIGHT)
                    progress_canvas.itemconfigure(progress_text, text="0%")
                    cancel_button.configure(state="disabled")
                    progress_canvas.itemconfigure(progress_text, state="hidden")
                    messagebox.showinfo("Cancelled", "Translation was cancelled.")
                app.after(0, handle_cancel_ui)
                break

            batch_ids = []
            batch_originals = []
            batch_indexes = []
            current_batch = lines[i:i + batch_size]

            for j, line in enumerate(current_batch):
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2 and re.search(r'[가-힣]', parts[1]):
                    batch_ids.append(parts[0])
                    batch_originals.append(parts[1])
                    batch_indexes.append(i + j)
                else:
                    translated_lines.append(line.rstrip("\n") + "\n")

            translated_batch = []

            if batch_originals:
                for index, original_text in enumerate(batch_originals):
                    try:
                        if original_text in translation_cache:
                            translated = translation_cache[original_text]
                        else:
                            translated = translator.translate(original_text, src='ko', dest='en').text
                            translation_cache[original_text] = translated
                        translated_batch.append(translated)
                    except Exception:
                        try:
                            translated = translator.translate(original_text, src='ko', dest='en').text
                            translation_cache[original_text] = translated
                            translated_batch.append(translated)
                        except Exception as e:
                            print(f"Retry failed for line {i + index + 1}: {e}")
                            translated_batch.append(None)

                for idx, translated in enumerate(translated_batch):
                    if translated is not None:
                        full_line = f"{batch_ids[idx]}\t{translated.strip()}\n"
                    else:
                        full_line = lines[batch_indexes[idx]]
                    translated_lines.append(full_line)

            progress = min(i + batch_size, total_lines) / total_lines
            current_fill = progress_canvas.coords(bar_fill)[2] / PROGRESS_WIDTH  # Get current width percent
            smooth_progress_update(current_fill, progress)

            i += batch_size
            time.sleep(0.3)

        if not cancel_requested:
            with open(output_path, 'w', encoding='utf-16') as f:
                f.writelines(translated_lines)
            save_cache()

            def handle_success_ui():
                progress_canvas.coords(bar_fill, 0, 0, 0, 24)
                progress_canvas.itemconfigure(progress_text, text="0%")
                cancel_button.configure(state="disabled")
                progress_canvas.itemconfigure(progress_text, state="hidden")
                messagebox.showinfo("Translation Complete", f"Saved to:\n{output_path}")

            app.after(0, handle_success_ui)

    threading.Thread(target=process_file).start()

def translate_selected_text():
    try:
        selected = korean_box.get("sel.first", "sel.last").strip()
        if not selected:
            raise ValueError  # Triggers the "no selection" behavior
        if selected in translation_cache:
            result = translation_cache[selected]
        else:
            result = translator.translate(selected, src='ko', dest='en').text
            translation_cache[selected] = result
            save_cache()
        english_box.configure(state="normal")
        english_box.delete("1.0", "end")
        english_box.insert("1.0", result)
        english_box.configure(state="disabled")
    except Exception:
        # Clear output if no valid selection
        english_box.configure(state="normal")
        english_box.delete("1.0", "end")
        english_box.insert("1.0", "")  # optional: insert a placeholder
        english_box.configure(state="disabled")

# === BUTTON STYLE ===
BUTTON_COLOR = "#0078D7"
HOVER_COLOR = "#106EBE"
FG_COLOR = "#ffffff"

def create_hover_button(parent, text, command):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=BUTTON_COLOR,
        hover_color=HOVER_COLOR,
        text_color=FG_COLOR,
        font=DEFAULT_FONT,
        corner_radius=8,
        width=135,
        height=32,
    )

# === GUI SETUP ===
app = ctk.CTk()
# Set window size
window_width = 600
window_height = 480

# Get screen dimensions
screen_width = app.winfo_screenwidth()
screen_height = app.winfo_screenheight()

# Calculate position (uses same style as Manual Maker)
position_x = int(((screen_width // 2) - (window_width // 2)) * 2)
position_y = int(((screen_height // 2) - (window_height // 2)) * 2)

# Apply centered geometry
app.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")

app.configure(fg_color="#1E1E1E")
icon_path = os.path.join(os.path.dirname(__file__), "blank.ico")
app.iconbitmap(icon_path)
app.title("")
app.resizable(False, False)

DEFAULT_FONT = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
TITLE_FONT = ctk.CTkFont(family="Segoe UI", size=18, weight="bold")

title_label = ctk.CTkLabel(app, text="PLC Translator", font=TITLE_FONT, text_color=FG_COLOR)
title_label.pack(pady=5)

# Buttons
button_frame = ctk.CTkFrame(app, fg_color="transparent")
button_frame.pack(pady=5)

create_hover_button(button_frame, "Translate .txt File", translate_file) \
    .pack(side="left", expand=True, fill="x", padx=5)
create_hover_button(button_frame, "Clear Translation Cache", clear_cache) \
    .pack(side="left", expand=True, fill="x", padx=5)

# Textboxes
text_frame = ctk.CTkFrame(app, fg_color="black")
text_frame.pack(padx=10, pady=(0, 0), fill="both", expand=True)

korean_box = ctk.CTkTextbox(text_frame, wrap="word", height=8, font=DEFAULT_FONT, border_color=BUTTON_COLOR, border_width=2, corner_radius=6)
korean_box.pack(side="left", padx=(0, 5), fill="both", expand=True)

english_box = ctk.CTkTextbox(text_frame, wrap="word", state="disabled", height=8, font=DEFAULT_FONT, border_color=BUTTON_COLOR, border_width=2, corner_radius=6)
english_box.pack(side="left", padx=(5, 0), fill="both", expand=True)

# Clear English box if Korean box is empty
def clear_english_if_empty(event=None):
    content = korean_box.get("1.0", "end").strip()
    if content == "":
        english_box.configure(state="normal")
        english_box.delete("1.0", "end")
        english_box.configure(state="disabled")
        
PLACEHOLDER = "Type or paste text to translate"
placeholder_active = True  # Tracks if placeholder is currently showing

def show_placeholder():
    global placeholder_active
    korean_box.configure(state="normal")
    korean_box.delete("1.0", "end")
    korean_box.insert("1.0", PLACEHOLDER)
    korean_box.configure(state="disabled", text_color="gray")
    placeholder_active = True

def clear_placeholder(event=None):
    global placeholder_active
    if placeholder_active:
        korean_box.configure(state="normal")
        korean_box.delete("1.0", "end")
        korean_box.configure(text_color="white")
        placeholder_active = False

def handle_key(event=None):
    global placeholder_active
    if placeholder_active:
        clear_placeholder()
    # If the user deletes everything, don't lock the box immediately

def handle_focus_out(event=None):
    content = korean_box.get("1.0", "end").strip()
    if content == "":
        show_placeholder()

# Set placeholder on startup
show_placeholder()

def handle_keyrelease(event=None):
    handle_key()
    clear_english_if_empty()
    schedule_auto_translate()

# Bind events
korean_box.bind("<FocusIn>", clear_placeholder)
korean_box.bind("<FocusOut>", handle_focus_out)
korean_box.bind("<KeyRelease>", handle_keyrelease)

def translate_all_text(event=None):
    text = korean_box.get("1.0", "end").strip()
    
    if not re.search(r'[가-힣]', text):
        return

    if not text:
        english_box.configure(state="normal")
        english_box.delete("1.0", "end")
        english_box.configure(state="disabled")
        return

    if text in translation_cache:
        result = translation_cache[text]
    else:
        try:
            result = translator.translate(text, src="ko", dest="en").text
        except Exception:
            result = "Translation not found in cache.\nPlease connect to the internet to translate this text."

    # Show it
    english_box.configure(state="normal")
    english_box.delete("1.0", "end")
    english_box.insert("1.0", result)
    english_box.configure(state="disabled")

def schedule_auto_translate(event=None):
    # wait 300ms after typing stops
    if hasattr(app, "_auto_id"):
        app.after_cancel(app._auto_id)
    app._auto_id = app.after(300, translate_all_text)
    
korean_box.bind("<<Paste>>", schedule_auto_translate)


# Bottom persistent bar
bottom_frame = ctk.CTkFrame(app, fg_color="#1E1E1E")
bottom_frame.pack(fill="x", pady=(5, 10))

PROGRESS_WIDTH = 800
PROGRESS_HEIGHT = 34
progress_canvas = Canvas(bottom_frame, width=PROGRESS_WIDTH, height=PROGRESS_HEIGHT, bg="black", highlightthickness=0)
progress_canvas.pack(padx=5, pady=2)

bar_bg = progress_canvas.create_rectangle(0, 0, PROGRESS_WIDTH, PROGRESS_HEIGHT, fill="#1E1E1E", width=0)
bar_fill = progress_canvas.create_rectangle(0, 0, 0, PROGRESS_HEIGHT, fill=BUTTON_COLOR, width=0)
progress_text = progress_canvas.create_text(PROGRESS_WIDTH // 2, PROGRESS_HEIGHT // 2, text="0%", fill="white", font=("Segoe UI", 14, "bold"))
progress_canvas.itemconfigure(progress_text, state="hidden")

cancel_button = ctk.CTkButton(bottom_frame, text="Cancel Translation", command=cancel_translation, corner_radius=8, fg_color=BUTTON_COLOR, hover_color=HOVER_COLOR, state="disabled", font=DEFAULT_FONT)
cancel_button.pack(pady=5)

app.mainloop()
