import customtkinter as ctk
from tkinter import filedialog, messagebox
from googletrans import Translator
import threading
import re
import time
import os
import json

# App appearance
ctk.set_appearance_mode("System")
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

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(input_path, 'r', encoding='utf-16') as f:
                lines = f.readlines()

        total_lines = len(lines)
        translated_lines = []

        app.after(0, lambda: progress_bar.set(0))
        app.after(0, lambda: progress_label.configure(text="Progress: 0%"))
        app.after(0, lambda: cancel_button.configure(state="normal"))

        i = 0
        while i < total_lines:
            if cancel_requested:
                def handle_cancel_ui():
                    progress_bar.set(0.0)
                    progress_label.configure(text="Progress: 0%")
                    cancel_button.configure(state="disabled")
                    messagebox.showinfo("Cancelled", "Translation was cancelled.")
                app.after(0, handle_cancel_ui)
                break

            batch_ids = []
            batch_originals = []
            batch_indexes = []
            current_batch = lines[i:i + batch_size]

            for j, line in enumerate(current_batch):
                parts = line.strip("\n").split("\t")
                if len(parts) >= 2 and re.search(r'[가-힣]', parts[1]):
                    batch_ids.append(parts[0])
                    batch_originals.append(parts[1])
                    batch_indexes.append(i + j)
                else:
                    translated_lines.append(line)

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
            app.after(0, lambda p=progress: progress_bar.set(p))
            app.after(0, lambda p=progress: progress_label.configure(text=f"Progress: {int(p * 100)}%"))

            i += batch_size
            time.sleep(0.3)

        if not cancel_requested:
            with open(output_path, 'w', encoding='utf-16') as f:
                f.writelines(translated_lines)
            save_cache()
            app.after(0, lambda: messagebox.showinfo("Translation Complete", f"Saved to:\n{output_path}"))

        app.after(0, lambda: cancel_button.configure(state="disabled"))

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
BUTTON_COLOR = "#1f6aa5"
HOVER_COLOR = "#174c7a"
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
        corner_radius=6,
        width=135,
        height=32
    )

# === GUI SETUP ===
app = ctk.CTk()
app.title("PLC Translator")
app.geometry("600x480+640+340")
app.resizable(False, False)

DEFAULT_FONT = ctk.CTkFont(size=14, weight="bold")
TITLE_FONT = ctk.CTkFont(size=18, weight="bold")

title_label = ctk.CTkLabel(app, text="PLC Translator", font=TITLE_FONT, text_color=FG_COLOR)
title_label.pack(pady=5)

# Buttons
button_frame = ctk.CTkFrame(app)
button_frame.pack(pady=5)

create_hover_button(button_frame, "Translate Full .txt File", translate_file) \
    .pack(side="left", expand=True, fill="x", padx=5)
create_hover_button(button_frame, "Clear Translation Cache", clear_cache) \
    .pack(side="left", expand=True, fill="x", padx=5)

# Textboxes
text_frame = ctk.CTkFrame(app)
text_frame.pack(padx=10, pady=(0, 0), fill="both", expand=True)

korean_box = ctk.CTkTextbox(text_frame, wrap="word", height=8)
korean_box.pack(side="left", padx=(0, 5), fill="both", expand=True)

english_box = ctk.CTkTextbox(text_frame, wrap="word", state="disabled", height=8)
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

# Bind events
korean_box.bind("<FocusIn>", clear_placeholder)
korean_box.bind("<FocusOut>", handle_focus_out)
korean_box.bind("<KeyRelease>", handle_key)

korean_box.bind("<KeyRelease>", clear_english_if_empty)

def translate_all_text(event=None):
    text = korean_box.get("1.0", "end").strip()
    if not text:
        # clear the right box if left is empty
        english_box.configure(state="normal")
        english_box.delete("1.0", "end")
        english_box.configure(state="disabled")
        return

    # either pull from cache or call Google Translate
    if text in translation_cache:
        result = translation_cache[text]
    else:
        result = translator.translate(text, src="ko", dest="en").text
        translation_cache[text] = result
        save_cache()

    # show it
    english_box.configure(state="normal")
    english_box.delete("1.0", "end")
    english_box.insert("1.0", result)
    english_box.configure(state="disabled")

def schedule_auto_translate(event=None):
    # wait 300ms after typing stops
    if hasattr(app, "_auto_id"):
        app.after_cancel(app._auto_id)
    app._auto_id = app.after(300, translate_all_text)
    
korean_box.bind("<KeyRelease>", schedule_auto_translate)
korean_box.bind("<<Paste>>", schedule_auto_translate)


# Bottom persistent bar
bottom_frame = ctk.CTkFrame(app)
bottom_frame.pack(fill="x", pady=(5, 10))

progress_bar = ctk.CTkProgressBar(bottom_frame, mode="determinate")
progress_bar.pack(fill="x", padx=10, pady=2)
progress_bar.set(0)

progress_label = ctk.CTkLabel(bottom_frame, text="Progress: 0%")
progress_label.pack()

cancel_button = ctk.CTkButton(bottom_frame, text="Cancel Translation", command=cancel_translation, fg_color="red", hover_color="#bb0000", state="disabled")
cancel_button.pack(pady=5)

app.mainloop()
