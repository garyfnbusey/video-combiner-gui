import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os
import json

# Default settings
settings = {
    "vcodec": "libx264",
    "acodec": "aac",
    "crf": "18",
    "preset": "fast",
    "resolution": "original"
}

def ffprobe_get_streams(file):
    """Return codec, resolution, framerate, audio codec for a file using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,width,height,r_frame_rate",
            "-of", "json", file
        ]
        video_info = subprocess.check_output(cmd, text=True)
        video_stream = json.loads(video_info)["streams"][0]

        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "json", file
        ]
        audio_info = subprocess.check_output(cmd, text=True)
        audio_streams = json.loads(audio_info).get("streams", [])
        audio_codec = audio_streams[0]["codec_name"] if audio_streams else None

        return {
            "vcodec": video_stream["codec_name"],
            "width": video_stream["width"],
            "height": video_stream["height"],
            "fps": eval(video_stream["r_frame_rate"]),
            "acodec": audio_codec,
        }
    except Exception as e:
        messagebox.showerror("Error", f"ffprobe failed for {file}:\n{e}")
        return None


def select_files():
    files = filedialog.askopenfilenames(
        title="Select MP4 files to combine",
        filetypes=[("MP4 files", "*.mp4")]
    )
    if files:
        file_list.delete(0, tk.END)
        # Sort alphabetically
        for f in sorted(files):
            file_list.insert(tk.END, f)


def move_up():
    selection = file_list.curselection()
    if not selection:
        return
    index = selection[0]
    if index == 0:
        return
    text = file_list.get(index)
    file_list.delete(index)
    file_list.insert(index - 1, text)
    file_list.select_set(index - 1)


def move_down():
    selection = file_list.curselection()
    if not selection:
        return
    index = selection[0]
    if index == file_list.size() - 1:
        return
    text = file_list.get(index)
    file_list.delete(index)
    file_list.insert(index + 1, text)
    file_list.select_set(index + 1)


def combine_videos():
    if file_list.size() == 0:
        messagebox.showerror("Error", "No files selected")
        return

    first_info = ffprobe_get_streams(file_list.get(0))
    if not first_info:
        return

    mismatch = False
    for i in range(1, file_list.size()):
        info = ffprobe_get_streams(file_list.get(i))
        if not info:
            return
        if info != first_info:
            mismatch = True
            break

    output_file = filedialog.asksaveasfilename(
        title="Save combined video as",
        defaultextension=".mp4",
        filetypes=[("MP4 files", "*.mp4")]
    )
    if not output_file:
        return

    if mismatch:
        choice = messagebox.askyesno(
            "Mismatch Detected",
            "The selected files have different codecs, resolutions, or framerates.\n\n"
            "Do you want to re-encode them to make concatenation possible?\n\n"
            "Yes = Re-encode (slower, but works)\nNo = Cancel"
        )
        if not choice:
            return

        temp_files = []
        for i in range(file_list.size()):
            infile = file_list.get(i)
            temp_out = f"temp_{i}.mp4"

            # Build scale filter
            if settings["resolution"] == "original":
                scale_filter = f"fps={first_info['fps']}"
            else:
                scale_filter = f"scale={settings['resolution']},fps={first_info['fps']}"

            cmd = [
                "ffmpeg", "-i", infile,
                "-vf", scale_filter,
                "-c:v", settings["vcodec"], "-preset", settings["preset"], "-crf", settings["crf"],
                "-c:a", settings["acodec"] if settings["acodec"] != "copy" else "copy",
                temp_out, "-y"
            ]
            subprocess.run(cmd, check=True)
            temp_files.append(temp_out)

        with open("input.txt", "w", encoding="utf-8") as f:
            for t in temp_files:
                f.write(f"file '{os.path.abspath(t)}'\n")

        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", "input.txt", "-c", "copy", output_file, "-y"
        ]
        subprocess.run(cmd, check=True)

        for t in temp_files:
            os.remove(t)
        os.remove("input.txt")

    else:
        with open("input.txt", "w", encoding="utf-8") as f:
            for i in range(file_list.size()):
                f.write(f"file '{file_list.get(i)}'\n")

        cmd = [
            "ffmpeg", "-f", "concat", "-safe", "0",
            "-i", "input.txt", "-c", "copy", output_file, "-y"
        ]
        subprocess.run(cmd, check=True)
        os.remove("input.txt")

    messagebox.showinfo("Success", f"Video saved to:\n{output_file}")


def open_settings():
    win = tk.Toplevel(root)
    win.title("Re-encode Settings")
    win.grab_set()

    def save_and_close():
        settings["vcodec"] = vcodec_var.get()
        settings["acodec"] = acodec_var.get()
        settings["crf"] = crf_var.get()
        settings["preset"] = preset_var.get()
        settings["resolution"] = res_var.get()
        win.destroy()

    ttk.Label(win, text="Video Codec:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    vcodec_var = tk.StringVar(value=settings["vcodec"])
    ttk.Combobox(win, textvariable=vcodec_var, values=["libx264", "libx265", "vp9"]).grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(win, text="Audio Codec:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    acodec_var = tk.StringVar(value=settings["acodec"])
    ttk.Combobox(win, textvariable=acodec_var, values=["aac", "mp3", "copy"]).grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(win, text="CRF (0=lossless, 18=good, 23=default):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
    crf_var = tk.StringVar(value=settings["crf"])
    ttk.Entry(win, textvariable=crf_var).grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(win, text="Preset:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
    preset_var = tk.StringVar(value=settings["preset"])
    ttk.Combobox(win, textvariable=preset_var, values=["ultrafast","superfast","veryfast","faster","fast","medium","slow","slower","veryslow"]).grid(row=3, column=1, padx=5, pady=5)

    ttk.Label(win, text="Resolution:").grid(row=4, column=0, sticky="w", padx=5, pady=5)
    res_var = tk.StringVar(value=settings["resolution"])
    ttk.Combobox(win, textvariable=res_var, values=["original","1920:1080","1280:720","640:480"]).grid(row=4, column=1, padx=5, pady=5)

    ttk.Button(win, text="Save", command=save_and_close).grid(row=5, column=0, columnspan=2, pady=10)


# GUI
root = tk.Tk()
root.title("MP4 Concatenator")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

btn_select = tk.Button(frame, text="Select MP4 Files", command=select_files)
btn_select.pack(fill="x")

file_list = tk.Listbox(frame, width=80, height=10, selectmode=tk.SINGLE)
file_list.pack(pady=5)

btn_frame = tk.Frame(frame)
btn_frame.pack(fill="x", pady=2)
tk.Button(btn_frame, text="Move Up", command=move_up).pack(side="left", expand=True, fill="x", padx=2)
tk.Button(btn_frame, text="Move Down", command=move_down).pack(side="left", expand=True, fill="x", padx=2)

btn_combine = tk.Button(frame, text="Combine Videos", command=combine_videos)
btn_combine.pack(fill="x", pady=2)

btn_settings = tk.Button(frame, text="Settings", command=open_settings)
btn_settings.pack(fill="x", pady=2)

root.mainloop()
