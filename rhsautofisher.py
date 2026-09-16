"""
Auto Fisher - GUI version

Listens to your system audio (loopback) and double-clicks when a sound
above a set threshold is detected. If nothing is detected for a while,
it single-clicks to re-cast, assuming something went wrong.

Dependencies:
    pip install soundcard pydirectinput keyboard numpy

Note: keyboard (for the global hotkey) usually needs the script to be
run as Administrator on Windows to detect key presses reliably.
"""

import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import soundcard as sc
import pydirectinput
import keyboard

# --- Defaults ---
DEFAULTS = {
    "threshold": 0.01,
    "chunk_size": 2048,
    "sample_rate": 48000,
    "cooldown": 0.25,
    "click_delay": 0.1,
    "silence_timeout": 20.0,
}
DEFAULT_HOTKEY = "f1"

pydirectinput.FAILSAFE = False


class AutoFisherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Fisher")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.running = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.current_hotkey = DEFAULT_HOTKEY
        self.hotkey_handle = None
        self.waiting_for_key = False

        # Tkinter variables for each setting (stored as strings, validated on use)
        self.vars = {
            "threshold": tk.StringVar(value=str(DEFAULTS["threshold"])),
            "chunk_size": tk.StringVar(value=str(DEFAULTS["chunk_size"])),
            "sample_rate": tk.StringVar(value=str(DEFAULTS["sample_rate"])),
            "cooldown": tk.StringVar(value=str(DEFAULTS["cooldown"])),
            "click_delay": tk.StringVar(value=str(DEFAULTS["click_delay"])),
            "silence_timeout": tk.StringVar(value=str(DEFAULTS["silence_timeout"])),
        }

        self.rms_var = tk.StringVar(value="RMS: --")
        self.status_var = tk.StringVar(value="Stopped")
        self.hotkey_var = tk.StringVar(value=f"Hotkey: {self.current_hotkey.upper()}")

        self._build_ui()
        self._register_hotkey(self.current_hotkey)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        float_fields = [
            ("threshold", "Threshold"),
            ("cooldown", "Cooldown (s)"),
            ("click_delay", "Click Delay (s)"),
            ("silence_timeout", "Silence Timeout (s)"),
        ]
        int_fields = [
            ("chunk_size", "Chunk Size"),
            ("sample_rate", "Sample Rate"),
        ]

        vcmd_float = (self.root.register(self._validate_float), "%P")
        vcmd_int = (self.root.register(self._validate_int), "%P")

        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True, **pad)

        row = 0
        for key, label in float_fields:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
            entry = ttk.Entry(
                frame, textvariable=self.vars[key], width=12,
                validate="key", validatecommand=vcmd_float,
            )
            entry.grid(row=row, column=1, **pad)
            row += 1

        for key, label in int_fields:
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", **pad)
            entry = ttk.Entry(
                frame, textvariable=self.vars[key], width=12,
                validate="key", validatecommand=vcmd_int,
            )
            entry.grid(row=row, column=1, **pad)
            row += 1

        ttk.Button(frame, text="Reset to Defaults", command=self._reset_defaults).grid(
            row=row, column=0, columnspan=2, sticky="ew", **pad
        )
        row += 1

        ttk.Separator(frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky="ew", pady=6
        )
        row += 1

        ttk.Label(frame, textvariable=self.hotkey_var).grid(
            row=row, column=0, sticky="w", **pad
        )
        ttk.Button(frame, text="Change Hotkey", command=self._start_hotkey_capture).grid(
            row=row, column=1, **pad
        )
        row += 1

        self.toggle_button = ttk.Button(
            frame, text="Start", command=self._toggle_running
        )
        self.toggle_button.grid(row=row, column=0, columnspan=2, sticky="ew", **pad)
        row += 1

        ttk.Label(frame, textvariable=self.status_var, foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", **pad
        )
        row += 1

        ttk.Label(frame, textvariable=self.rms_var, foreground="gray").grid(
            row=row, column=0, columnspan=2, sticky="w", **pad
        )
        row += 1

    # ---------- Validation ----------

    @staticmethod
    def _validate_float(proposed):
        if proposed == "":
            return True
        try:
            float(proposed)
            return True
        except ValueError:
            return False

    @staticmethod
    def _validate_int(proposed):
        if proposed == "":
            return True
        return proposed.isdigit()

    def _reset_defaults(self):
        for key, value in DEFAULTS.items():
            self.vars[key].set(str(value))

    def _get_settings(self):
        """Read current field values, falling back to defaults for blank/invalid entries."""
        settings = {}
        for key, default in DEFAULTS.items():
            raw = self.vars[key].get()
            try:
                settings[key] = float(raw) if isinstance(default, float) else int(raw)
            except ValueError:
                settings[key] = default
        return settings

    # ---------- Hotkey ----------

    def _register_hotkey(self, key):
        if self.hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_handle)
            except (KeyError, ValueError):
                pass
        self.hotkey_handle = keyboard.add_hotkey(key, self._toggle_running)
        self.current_hotkey = key
        self.hotkey_var.set(f"Hotkey: {key.upper()}")

    def _start_hotkey_capture(self):
        if self.waiting_for_key:
            return
        self.waiting_for_key = True
        self.hotkey_var.set("Press any key...")
        threading.Thread(target=self._capture_key_thread, daemon=True).start()

    def _capture_key_thread(self):
        event = keyboard.read_event(suppress=False)
        while event.event_type != keyboard.KEY_DOWN:
            event = keyboard.read_event(suppress=False)
        new_key = event.name
        self.root.after(0, lambda: self._finish_hotkey_capture(new_key))

    def _finish_hotkey_capture(self, new_key):
        self._register_hotkey(new_key)
        self.waiting_for_key = False

    # ---------- Macro control ----------

    def _toggle_running(self):
        if self.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        if self.running:
            return
        self.running = True
        self.stop_event.clear()
        self.toggle_button.config(text="Stop")
        self.status_var.set("Running")
        settings = self._get_settings()
        self.worker_thread = threading.Thread(
            target=self._worker_loop, args=(settings,), daemon=True
        )
        self.worker_thread.start()

    def _stop(self):
        self.running = False
        self.stop_event.set()
        self.toggle_button.config(text="Start")
        self.status_var.set("Stopped")

    def _on_close(self):
        self._stop()
        if self.hotkey_handle is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_handle)
            except (KeyError, ValueError):
                pass
        self.root.destroy()

    # ---------- Worker (runs in background thread) ----------

    def _worker_loop(self, settings):
        try:
            speaker = sc.default_speaker()
            mic = sc.get_microphone(speaker.name, include_loopback=True)
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Audio error: {e}"))
            self.root.after(0, self._stop)
            return

        last_trigger = 0.0
        last_activity = time.time()

        try:
            with mic.recorder(samplerate=settings["sample_rate"]) as recorder:
                while not self.stop_event.is_set():
                    try:
                        data = recorder.record(numframes=settings["chunk_size"])
                    except Exception:
                        time.sleep(0.05)
                        continue

                    rms = float(np.sqrt(np.mean(data ** 2)))
                    now = time.time()

                    self.root.after(0, lambda r=rms: self.rms_var.set(f"RMS: {r:.4f}"))

                    if rms > settings["threshold"] and (now - last_trigger) > settings["cooldown"]:
                        pydirectinput.leftClick()
                        time.sleep(settings["click_delay"])
                        pydirectinput.leftClick()
                        last_trigger = now
                        last_activity = now
                        self.root.after(0, lambda: self.status_var.set("Running - sound detected, double-clicked"))

                    elif (now - last_activity) > settings["silence_timeout"]:
                        pydirectinput.leftClick()
                        last_trigger = now
                        last_activity = now
                        self.root.after(0, lambda: self.status_var.set("Running - silence timeout, re-cast"))

        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error: {e}"))
            self.root.after(0, self._stop)


def main():
    root = tk.Tk()
    AutoFisherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()