import tkinter as tk
from PIL import Image, ImageTk, ImageOps
import pyaudio
import audioop
from tkinter import ttk
import json

# Initialize PyAudio
p = pyaudio.PyAudio()

# Function to open a stream with the selected microphone
def open_mic_stream(mic_index, gain):
    global stream
    if 'stream' in globals():
        stream.stop_stream()
        stream.close()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=44100,
                    input=True,
                    input_device_index=mic_index,
                    frames_per_buffer=1024)
    return stream

# Function to apply gain to raw audio data
def apply_gain(data, gain):
    return audioop.mul(data, 2, gain)

# Load images with alpha channel
quiet_image = Image.open("chibi/quiet.png").convert("RGBA")
normal_talk_image = Image.open("chibi/talking.png").convert("RGBA")
screaming_image = Image.open("chibi/screaming.png").convert("RGBA")


# Initialize Tkinter
window = tk.Tk()
window.title("Scream Detection Image Display")
window.geometry('800x600')

# Settings dictionary
settings = {
    "normal_talk_threshold": 5000,
    "scream_threshold": 10000,
    "gain": 1
}

# Load settings from file
def load_settings():
    try:
        with open('settings.json', 'r') as f:
            loaded_settings = json.load(f)
            normal_talk_scale.set(loaded_settings["normal_talk_threshold"])
            scream_scale.set(loaded_settings["scream_threshold"])
            gain_scale.set(loaded_settings["gain"])
            normal_talk_entry.delete(0, tk.END)
            normal_talk_entry.insert(0, str(loaded_settings["normal_talk_threshold"]))
            scream_entry.delete(0, tk.END)
            scream_entry.insert(0, str(loaded_settings["scream_threshold"]))
            gain_entry.delete(0, tk.END)
            gain_entry.insert(0, str(loaded_settings["gain"]))
    except FileNotFoundError:
        print("Settings file not found, using default values.")

# Save settings to file
def save_settings():
    settings["normal_talk_threshold"] = normal_talk_scale.get()
    settings["scream_threshold"] = scream_scale.get()
    settings["gain"] = gain_scale.get()
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

# Sensitivity settings frame
sensitivity_frame = tk.Frame(window)
sensitivity_frame.pack()

# Normal talk threshold
tk.Label(sensitivity_frame, text="Normal Talk Threshold").pack(side=tk.LEFT)
normal_talk_scale = tk.Scale(sensitivity_frame, from_=0, to=30000, orient=tk.HORIZONTAL, command=lambda val: normal_talk_entry.delete(0, tk.END) or normal_talk_entry.insert(0, val))
normal_talk_scale.pack(side=tk.LEFT)
normal_talk_entry = tk.Entry(sensitivity_frame, width=6)
normal_talk_entry.pack(side=tk.LEFT)
normal_talk_entry.bind('<Return>', lambda event: normal_talk_scale.set(normal_talk_entry.get()))

# Scream threshold
tk.Label(sensitivity_frame, text="Scream Threshold").pack(side=tk.LEFT)
scream_scale = tk.Scale(sensitivity_frame, from_=0, to=30000, orient=tk.HORIZONTAL, command=lambda val: scream_entry.delete(0, tk.END) or scream_entry.insert(0, val))
scream_scale.pack(side=tk.LEFT)
scream_entry = tk.Entry(sensitivity_frame, width=6)
scream_entry.pack(side=tk.LEFT)
scream_entry.bind('<Return>', lambda event: scream_scale.set(scream_entry.get()))

# Gain control
tk.Label(sensitivity_frame, text="Microphone Gain").pack(side=tk.LEFT)
gain_scale = tk.Scale(sensitivity_frame, from_=1, to=10, orient=tk.HORIZONTAL, command=lambda val: gain_entry.delete(0, tk.END) or gain_entry.insert(0, val))
gain_scale.pack(side=tk.LEFT)
gain_entry = tk.Entry(sensitivity_frame, width=6)
gain_entry.pack(side=tk.LEFT)
gain_entry.bind('<Return>', lambda event: gain_scale.set(gain_entry.get()))

# Image label that resizes with the window
image_label = tk.Label(window)
image_label.pack(fill=tk.BOTH, expand=tk.YES)

# Audio level meter
level_meter = ttk.Progressbar(window, orient='horizontal', length=200, mode='determinate')
level_meter.pack()

# Noise gate thresholds
open_threshold = 6000  # Volume level to open the gate
close_threshold = 3000  # Volume level to close the gate
gate_open = False  # Initial state of the gate

# Initialize noise gate thresholds and state
open_threshold = 6000  # The threshold above which the gate opens
close_threshold = 3000  # The threshold below which the gate closes
gate_open = False  # The initial state of the gate is closed

def update_image():
    global gate_open  # Use the global variable to maintain gate state across function calls

    try:
        data = stream.read(1024, exception_on_overflow=False)
        data = apply_gain(data, gain_scale.get())
        volume = audioop.rms(data, 2)  # Get the volume (RMS)
        level_meter['value'] = volume  # Update the level meter

        # Noise gate logic
        if volume > open_threshold:
            gate_open = True
        elif volume < close_threshold:
            gate_open = False

        if gate_open or volume > normal_talk_scale.get():
            # If the gate is open or volume is above normal talk, update images normally
            if volume > scream_scale.get():
                img = screaming_image
            elif volume > normal_talk_scale.get():
                img = normal_talk_image
            else:
                img = quiet_image
        else:
            # If the gate is closed and volume is below normal talk, show quiet image
            img = quiet_image

        # The rest of the image updating logic remains the same
        img.thumbnail((image_label.winfo_width(), image_label.winfo_height()), Image.ANTIALIAS)
        green_screen = Image.new('RGBA', (img.width, img.height), color=(0, 255, 0, 255))
        combined = Image.alpha_composite(green_screen, img)
        photo = ImageTk.PhotoImage(combined)
        image_label.config(image=photo)
        image_label.image = photo

    except IOError as e:
        print(e)

    window.after(100, update_image)  # Continue updating the image every 100 ms

# Dropdown Menu for Microphone Selection
mic_label = tk.Label(window, text="Select Microphone:")
mic_label.pack()

mic_select = ttk.Combobox(window)
mic_select.pack()

def refresh_mic_list():
    mic_list = []
    current = mic_select.get()
    mic_select['values'] = []  # Clear current values
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info.get('maxInputChannels') > 0:
            mic_list.append(dev_info.get('name'))
    mic_select['values'] = mic_list
    if mic_list:
        try:
            current_index = mic_list.index(current)
            mic_select.current(current_index)
        except ValueError:
            mic_select.current(0)
        open_mic_stream(mic_select.current(), gain_scale.get())

def on_mic_select(event):
    mic_name = mic_select.get()
    for i in range(p.get_device_count()):
        dev_info = p.get_device_info_by_index(i)
        if dev_info['name'] == mic_name:
            open_mic_stream(i, gain_scale.get())
            break

mic_select.bind('<<ComboboxSelected>>', on_mic_select)
refresh_mic_list()

# Button to refresh microphone list
refresh_button = tk.Button(window, text="Refresh Microphones", command=refresh_mic_list)
refresh_button.pack()

# Button to save settings
save_button = tk.Button(window, text="Save Settings", command=save_settings)
save_button.pack()

# Start the update process
window.after(100, update_image)

# Load settings from file on start
load_settings()

# Run the Tkinter loop
window.mainloop()

# Close the stream
stream.stop_stream()
stream.close()
p.terminate()
