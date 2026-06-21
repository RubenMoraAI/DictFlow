import keyboard
import sounddevice as sd
import wave
import tempfile
import os
import math
import array
import random
import pyperclip
from pynput.mouse import Controller
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import sys
from transcription_history import TranscriptionHistory
from text_enhancer import TextEnhancer
from context_detector import detect_context, get_active_monitor_work_area
from datetime import datetime, timedelta
import json
import customtkinter as ctk
import logging
import webbrowser

# Configure the logging system
def setup_logging():
    # Get the application directory path
    if getattr(sys, 'frozen', False):
        # Running as a bundled executable
        app_dir = os.path.dirname(sys.executable)
    else:
        # Running in development
        app_dir = os.path.dirname(os.path.abspath(__file__))

    # Create the logs directory if it does not exist
    log_dir = os.path.join(app_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    # Configure the log file
    log_file = os.path.join(log_dir, 'dictflow.log')

    # Configure the logging format
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()  # Also print to the console
        ]
    )

    # Initial log
    logging.info('Iniciando DictFlow')
    logging.info(f'Directorio de la aplicación: {app_dir}')
    logging.info(f'Archivo de log: {log_file}')

# Configure the global exception handler
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Excepción no manejada:", exc_info=(exc_type, exc_value, exc_traceback))

# Install the exception handler
sys.excepthook = handle_exception

# Start the logging system
setup_logging()

# Recording configuration
# 16 kHz mono is the standard for speech recognition: same accuracy as
# 44.1 kHz but ~2.75x less data, which speeds up the upload to Gemini.
CHUNK = 1024
CHANNELS = 1
RATE = 16000
SAMPLE_WIDTH = 2  # bytes per sample for 16-bit PCM audio

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, history, text_enhancer, app):
        super().__init__(parent)
        self.parent = parent
        self.history = history
        self.text_enhancer = text_enhancer
        self.app = app
        self.gemini_models = [
            "gemini-2.5-flash",
            "gemini-flash-latest",
            "gemini-2.5-pro"
        ]

        self.title("DictFlow - Configuración")
        self.geometry("1000x700")

        self.update_idletasks()
        width = 1000
        height = 700
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

        # Save the default colors so they can be reverted later
        self._default_selected_color = ctk.ThemeManager.theme["CTkSegmentedButton"]["selected_color"]
        self._default_selected_hover_color = ctk.ThemeManager.theme["CTkSegmentedButton"]["selected_hover_color"]

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.tabview = ctk.CTkTabview(self, command=self.on_tab_change)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tabview.add("API")
        self.tabview.add("Historial")
        self.tabview.add("Estadísticas")
        self.tabview.add("Configuración")
        self.tabview.add("Atajos")
        self.tabview.add("Formato por App")
        self.tabview.add("Vocabulario")
        self.tabview.add("Modelo Gemini")
        self.tabview.add("Donar")

        # --- Custom color for the "Donar" tab button ---
        # This ensures the tab button itself has a unique color, even when not selected.
        # We use a slightly darker yellow for the non-selected state.
        donate_fg_color = "#B8860B"  # DarkGoldenRod
        donate_hover_color = "#DAA520" # GoldenRod
        donate_text_color = "#FFFFFF" # White text for better contrast

        try:
            # Access the internal button dictionary to configure a specific tab button
            donate_button = self.tabview._segmented_button._buttons_dict["Donar"]
            donate_button.configure(
                fg_color=donate_fg_color,
                hover_color=donate_hover_color,
                text_color=donate_text_color
            )
        except (AttributeError, KeyError) as e:
            logging.warning(f"Could not apply custom color to 'Donar' tab: {e}")

        self.setup_api_tab()
        self.setup_history_tab()
        self.setup_stats_tab()
        self.setup_config_tab()
        self.setup_shortcuts_tab()
        self.setup_app_formats_tab()
        self.setup_vocabulary_tab()
        self.setup_model_tab()
        self.setup_donate_tab()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.transient(parent)
        self.grab_set()

        self.update()
        self.deiconify()
        self.lift()
        self.focus_force()

    def on_tab_change(self):
        selected_tab = self.tabview.get()

        # A yellow/gold color that stands out
        donate_color = "#FFD700"  # Gold, for when selected
        donate_hover_color = "#FFC300"

        if selected_tab == "Donar":
            self.tabview.configure(
                segmented_button_selected_color=donate_color,
                segmented_button_selected_hover_color=donate_hover_color
            )
        else:
            # Revert to the theme's default colors
            self.tabview.configure(
                segmented_button_selected_color=self._default_selected_color,
                segmented_button_selected_hover_color=self._default_selected_hover_color
            )

    def setup_api_tab(self):
        tab = self.tabview.tab("API")

        title = ctk.CTkLabel(tab, text="Configuración de la API de Gemini", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 20))

        api_frame = ctk.CTkFrame(tab)
        api_frame.pack(fill="x", padx=10, pady=10)

        label = ctk.CTkLabel(api_frame, text="API Key:", width=100)
        label.pack(side="left", padx=5)

        api_entry = ctk.CTkEntry(api_frame, width=400, show="*")
        api_entry.pack(side="left", fill="x", expand=True, padx=5)

        if self.text_enhancer.api_key:
            api_entry.insert(0, self.text_enhancer.api_key)

        def save_api_key():
            api_key = api_entry.get().strip()
            if self.text_enhancer.set_api_key(api_key):
                messagebox.showinfo(
                    "Éxito",
                    "API Key guardada y verificada correctamente.\n"
                    "La prueba de generación funcionó. ✅",
                    parent=self
                )
            else:
                detalle = self.text_enhancer.last_error or "Verifica la clave."
                if len(detalle) > 400:
                    detalle = detalle[:400] + "..."
                messagebox.showerror(
                    "Error",
                    "La API Key no funcionó en la prueba de generación.\n\n"
                    f"Detalle:\n{detalle}",
                    parent=self
                )

        save_button = ctk.CTkButton(tab, text="Guardar y Activar API", command=save_api_key)
        save_button.pack(pady=20)

    def setup_history_tab(self):
        tab = self.tabview.tab("Historial")

        title = ctk.CTkLabel(tab, text="Historial de Transcripciones", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 20))

        frame = ctk.CTkScrollableFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        history_entries = self.history.get_recent_transcriptions(10)

        if not history_entries:
            ctk.CTkLabel(frame, text="No hay transcripciones en el historial.").pack(pady=10)
        else:
            for entry in history_entries:
                entry_frame = ctk.CTkFrame(frame)
                entry_frame.pack(fill="x", pady=5, padx=5)

                timestamp = datetime.fromisoformat(entry['timestamp'])
                formatted_time = timestamp.strftime("%d/%m/%Y %H:%M:%S")

                info_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
                info_frame.pack(fill="x", padx=10, pady=(10, 0))

                ctk.CTkLabel(info_frame, text=formatted_time, text_color="#4EC9B0").pack(side="left")
                ctk.CTkLabel(info_frame, text=f"Duración: {entry['duration']:.2f}s", text_color="#9CDCFE").pack(side="left", padx=(10, 0))

                mode_text = "Modo Gemini"
                if entry.get('used_gemini', False):
                    mode_text += " + Mejoras"
                ctk.CTkLabel(info_frame, text=mode_text, text_color="#CE9178").pack(side="left", padx=(10, 0))

                text_frame = ctk.CTkFrame(entry_frame, fg_color="transparent")
                text_frame.pack(fill="x", padx=10, pady=(5, 10))

                def create_copy_button(text):
                    def copy_text():
                        pyperclip.copy(text)
                        button.configure(text="✓", fg_color="#4CAF50")
                        button.after(1000, lambda: button.configure(text="📋", fg_color="#0E639C"))
                    return copy_text

                button = ctk.CTkButton(text_frame, text="📋", width=30, command=create_copy_button(entry['text']), fg_color="#0E639C", hover_color="#1177BB")
                button.pack(side="left", padx=(0, 10))

                text_label = ctk.CTkLabel(text_frame, text=entry['text'], text_color="#DCDCAA", justify="left", wraplength=700)
                text_label.pack(side="left", fill="x", expand=True)

    def setup_stats_tab(self):
        tab = self.tabview.tab("Estadísticas")

        title = ctk.CTkLabel(tab, text="Estadísticas de Uso", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 20))

        stats = self.history.get_statistics()
        frame = ctk.CTkScrollableFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        def create_stat_section(title, data):
            section = ctk.CTkFrame(frame)
            section.pack(fill="x", pady=5, padx=5)
            ctk.CTkLabel(section, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)
            for key, value in data.items():
                row = ctk.CTkFrame(section, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=2)
                ctk.CTkLabel(row, text=f"{key}:").pack(side="left")
                ctk.CTkLabel(row, text=str(value)).pack(side="right")

        create_stat_section("Últimas 24 horas", {"Total transcripciones": stats['last_24h']['total'], "Con mejoras": stats['last_24h']['gemini']})
        create_stat_section("Última semana", {"Total transcripciones": stats['last_week']['total'], "Con mejoras": stats['last_week']['gemini']})
        create_stat_section("Último mes", {"Total transcripciones": stats['last_month']['total'], "Con mejoras": stats['last_month']['gemini']})
        create_stat_section("Totales", {"Peticiones a Gemini": stats['total_gemini_requests'], "Duración promedio": f"{stats['avg_duration']:.2f}s"})

    def setup_config_tab(self):
        tab = self.tabview.tab("Configuración")

        title = ctk.CTkLabel(tab, text="Master Prompt (pipeline de refinamiento)", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 20))

        prompt_frame = ctk.CTkFrame(tab)
        prompt_frame.pack(fill="both", expand=True, padx=10, pady=10)

        prompt_area = ctk.CTkTextbox(prompt_frame, font=("Consolas", 12))
        prompt_area.pack(fill="both", expand=True, padx=10, pady=10)

        current_prompt = self.text_enhancer.get_current_prompt()
        prompt_area.insert("1.0", current_prompt)

        def save_prompt():
            new_prompt = prompt_area.get("1.0", "end-1c").strip()
            if self.text_enhancer.update_prompt(new_prompt):
                messagebox.showinfo("Éxito", "Prompt actualizado correctamente", parent=self)
            else:
                messagebox.showerror("Error", "No se pudo actualizar el prompt", parent=self)

        save_button = ctk.CTkButton(tab, text="Guardar Prompt", command=save_prompt)
        save_button.pack(pady=10)

    @staticmethod
    def _shortcuts_to_text(shortcuts):
        """Render the shortcut dict as editable 'trigger = expansion' lines."""
        return "\n".join(f"{trigger} = {expansion}" for trigger, expansion in shortcuts.items())

    @staticmethod
    def _text_to_shortcuts(text):
        """Parse 'trigger = expansion' lines back into a dict (ignores blanks/#)."""
        result = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            trigger, expansion = line.split('=', 1)
            trigger = trigger.strip()
            if trigger:
                result[trigger] = expansion.strip()
        return result

    def setup_shortcuts_tab(self):
        tab = self.tabview.tab("Atajos")

        title = ctk.CTkLabel(tab, text="Atajos y expansiones de texto", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 5))

        help_text = ctk.CTkLabel(
            tab,
            text="Un atajo por línea con el formato:  disparador = expansión\n"
                 "Ej.:  ASAP = as soon as possible      |      mi dirección = Calle Falsa 123, Springfield\n"
                 "Al dictar el disparador, se sustituye exactamente por su expansión (sirve para forzar inglés).",
            font=("Arial", 11),
            text_color="#9CDCFE",
            justify="left"
        )
        help_text.pack(pady=(0, 10), padx=10)

        shortcuts_frame = ctk.CTkFrame(tab)
        shortcuts_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        shortcuts_area = ctk.CTkTextbox(shortcuts_frame, font=("Consolas", 12))
        shortcuts_area.pack(fill="both", expand=True, padx=10, pady=10)
        shortcuts_area.insert("1.0", self._shortcuts_to_text(self.text_enhancer.get_shortcuts()))

        # Output language selector
        lang_frame = ctk.CTkFrame(tab, fg_color="transparent")
        lang_frame.pack(fill="x", padx=10)
        ctk.CTkLabel(lang_frame, text="Idioma de salida:").pack(side="left", padx=(0, 10))

        lang_labels = {"auto": "Automático", "es": "Español", "en": "Inglés"}
        lang_values = {v: k for k, v in lang_labels.items()}
        lang_var = ctk.StringVar(value=lang_labels.get(self.text_enhancer.get_output_language(), "Automático"))
        lang_menu = ctk.CTkOptionMenu(lang_frame, values=list(lang_labels.values()), variable=lang_var)
        lang_menu.pack(side="left")

        # Recording hotkey (configurable)
        hk_frame = ctk.CTkFrame(tab, fg_color="transparent")
        hk_frame.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(hk_frame, text="Atajo de grabación:").pack(side="left", padx=(0, 10))
        hk_entry = ctk.CTkEntry(hk_frame, width=170)
        hk_entry.insert(0, self.text_enhancer.get_hotkey())
        hk_entry.pack(side="left", padx=(0, 10))
        hk_status = ctk.CTkLabel(hk_frame, text="ej.: ctrl+shift+q, pause, f9",
                                 text_color="#9CDCFE", font=("Arial", 10))
        hk_status.pack(side="left", padx=(8, 0))

        def cambiar_hotkey():
            nuevo = hk_entry.get().strip().lower()
            if self.app.cambiar_hotkey(nuevo):
                hk_status.configure(text=f"✓ Atajo activo: {nuevo}", text_color="#4CAF50")
            else:
                hk_status.configure(text="✗ Atajo inválido", text_color="#F44336")

        ctk.CTkButton(hk_frame, text="Cambiar", width=90, command=cambiar_hotkey,
                      fg_color="#1f6aa5").pack(side="left", padx=(10, 0))

        # Real-time (Live API) mode toggle
        rt_var = ctk.BooleanVar(value=self.text_enhancer.get_realtime_mode())

        def toggle_rt():
            self.text_enhancer.set_realtime_mode(rt_var.get())

        ctk.CTkCheckBox(
            tab, text="Modo tiempo real (Live API · experimental)",
            variable=rt_var, command=toggle_rt
        ).pack(pady=(12, 0), padx=10, anchor="w")

        # Microphone selection
        mic_frame = ctk.CTkFrame(tab, fg_color="transparent")
        mic_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(mic_frame, text="Micrófono:").pack(side="left", padx=(0, 10))
        mics = self.app.listar_microfonos()
        mic_names = [n for (_i, n) in mics]
        DEFAULT_MIC = "Predeterminado (sistema)"
        current_mic = self.text_enhancer.get_input_device_name()
        mic_var = ctk.StringVar(
            value=current_mic if current_mic in mic_names else DEFAULT_MIC
        )

        def on_mic(choice):
            self.text_enhancer.set_input_device_name(
                None if choice == DEFAULT_MIC else choice
            )

        ctk.CTkOptionMenu(mic_frame, values=[DEFAULT_MIC] + mic_names,
                          variable=mic_var, command=on_mic, width=260).pack(side="left")

        # Auto-stop on silence + sound feedback
        auto_var = ctk.BooleanVar(value=self.text_enhancer.get_auto_stop_silence())
        ctk.CTkCheckBox(
            tab, text="Auto-stop: parar al detectar silencio",
            variable=auto_var,
            command=lambda: self.text_enhancer.set_auto_stop_silence(auto_var.get())
        ).pack(pady=(10, 0), padx=10, anchor="w")

        sound_var = ctk.BooleanVar(value=self.text_enhancer.get_sound_feedback())
        ctk.CTkCheckBox(
            tab, text="Sonido al iniciar/parar la grabación",
            variable=sound_var,
            command=lambda: self.text_enhancer.set_sound_feedback(sound_var.get())
        ).pack(pady=(6, 0), padx=10, anchor="w")

        # Command (transform selected text) hotkey
        ch_frame = ctk.CTkFrame(tab, fg_color="transparent")
        ch_frame.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(ch_frame, text="Atajo de comando (transformar selección):").pack(side="left", padx=(0, 10))
        ch_entry = ctk.CTkEntry(ch_frame, width=150)
        ch_entry.insert(0, self.text_enhancer.get_command_hotkey())
        ch_entry.pack(side="left", padx=(0, 10))
        ch_status = ctk.CTkLabel(ch_frame, text="", text_color="#9CDCFE", font=("Arial", 10))
        ch_status.pack(side="left", padx=(8, 0))

        def cambiar_ch():
            nuevo = ch_entry.get().strip().lower()
            if self.app.cambiar_command_hotkey(nuevo):
                ch_status.configure(text=f"✓ {nuevo}", text_color="#4CAF50")
            else:
                ch_status.configure(text="✗ inválido", text_color="#F44336")

        ctk.CTkButton(ch_frame, text="Cambiar", width=90, command=cambiar_ch,
                      fg_color="#1f6aa5").pack(side="left", padx=(10, 0))

        def save_shortcuts():
            new_shortcuts = self._text_to_shortcuts(shortcuts_area.get("1.0", "end-1c"))
            self.text_enhancer.set_shortcuts(new_shortcuts)
            self.text_enhancer.set_output_language(lang_values.get(lang_var.get(), "auto"))
            save_button.configure(text="✓ Guardado", fg_color="#4CAF50")
            save_button.after(1000, lambda: save_button.configure(text="Guardar atajos", fg_color="#1f6aa5"))

        save_button = ctk.CTkButton(tab, text="Guardar atajos", command=save_shortcuts, fg_color="#1f6aa5")
        save_button.pack(pady=10)

    def setup_app_formats_tab(self):
        tab = self.tabview.tab("Formato por App")

        ctk.CTkLabel(tab, text="Formato por aplicación",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 4))
        ctk.CTkLabel(
            tab,
            text="Elige una app y define cómo se formatea el texto cuando dictas en ella.\n"
                 "Tiene prioridad sobre las reglas generales. La app activa se detecta sola.",
            font=("Arial", 11), text_color="#9CDCFE", justify="left"
        ).pack(pady=(0, 8), padx=10)

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=10)
        ctk.CTkLabel(top, text="Aplicación:").pack(side="left", padx=(0, 10))

        contexts = self.text_enhancer.get_known_contexts()
        sel = ctk.StringVar(value=contexts[0])
        state = {"current": contexts[0]}

        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        textbox = ctk.CTkTextbox(frame, font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)

        def load(ctx):
            textbox.delete("1.0", "end")
            textbox.insert("1.0", self.text_enhancer.get_context_prompt(ctx) or "")

        def on_select(choice):
            # Auto-save the app we are leaving, then load the chosen one.
            self.text_enhancer.set_context_prompt(state["current"], textbox.get("1.0", "end-1c").strip())
            state["current"] = choice
            load(choice)

        ctk.CTkOptionMenu(top, values=contexts, variable=sel,
                          command=on_select, width=200).pack(side="left")
        load(contexts[0])

        def save():
            self.text_enhancer.set_context_prompt(sel.get(), textbox.get("1.0", "end-1c").strip())
            save_button.configure(text="✓ Guardado", fg_color="#4CAF50")
            save_button.after(1200, lambda: save_button.configure(
                text="Guardar formato de esta app", fg_color="#1f6aa5"))

        save_button = ctk.CTkButton(tab, text="Guardar formato de esta app",
                                    command=save, fg_color="#1f6aa5")
        save_button.pack(pady=10)

    def setup_vocabulary_tab(self):
        tab = self.tabview.tab("Vocabulario")
        ctk.CTkLabel(tab, text="Vocabulario personalizado",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 4))
        ctk.CTkLabel(
            tab,
            text="Un término por línea: nombres propios, marcas, jerga o tecnicismos.\n"
                 "Se le indican al modelo para que los transcriba con la ortografía exacta.",
            font=("Arial", 11), text_color="#9CDCFE", justify="left"
        ).pack(pady=(0, 8), padx=10)

        frame = ctk.CTkFrame(tab)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        textbox = ctk.CTkTextbox(frame, font=("Consolas", 12))
        textbox.pack(fill="both", expand=True, padx=10, pady=10)
        textbox.insert("1.0", "\n".join(self.text_enhancer.get_vocabulary()))

        def save():
            terms = [t.strip() for t in textbox.get("1.0", "end-1c").splitlines() if t.strip()]
            self.text_enhancer.set_vocabulary(terms)
            save_button.configure(text="✓ Guardado", fg_color="#4CAF50")
            save_button.after(1200, lambda: save_button.configure(
                text="Guardar vocabulario", fg_color="#1f6aa5"))

        save_button = ctk.CTkButton(tab, text="Guardar vocabulario", command=save, fg_color="#1f6aa5")
        save_button.pack(pady=10)

    def setup_model_tab(self):
        tab = self.tabview.tab("Modelo Gemini")
        title = ctk.CTkLabel(tab, text="Selecciona el modelo de Gemini", font=ctk.CTkFont(size=16, weight="bold"))
        title.pack(pady=(10, 20))

        model_var = ctk.StringVar(value=self.text_enhancer.get_model())
        combobox = ctk.CTkComboBox(tab, values=self.gemini_models, variable=model_var, width=400)
        combobox.pack(pady=20)

        def save_model():
            nuevo_modelo = model_var.get()
            self.text_enhancer.set_model(nuevo_modelo)
            save_button.configure(text="✓ Guardado", fg_color="#4CAF50")
            save_button.after(1000, lambda: save_button.configure(text="Guardar modelo", fg_color="#1f6aa5"))

        save_button = ctk.CTkButton(tab, text="Guardar modelo", command=save_model, fg_color="#1f6aa5")
        save_button.pack(pady=10)

    def open_link(self, url: str):
        """Open a link in the default browser."""
        webbrowser.open_new(url)

    def setup_donate_tab(self):
        """Set up the Donation tab."""
        tab = self.tabview.tab("Donar")

        # Center the content within the tab
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        content_frame = ctk.CTkFrame(tab, fg_color="transparent")
        content_frame.grid(row=0, column=0, sticky="nsew")

        # Thank-you text
        text_label = ctk.CTkLabel(
            content_frame,
            text="Si te ha gustado esta aplicación, puedes hacer una donación.",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        text_label.pack(pady=(20, 10), padx=20)

        # Clickable link
        link_url = "https://buymeacoffee.com/joselabweb"
        link_font = ctk.CTkFont(size=14, underline=True)
        link_label = ctk.CTkLabel(
            content_frame, text=link_url, font=link_font, text_color="#60A5FA"
        )
        link_label.pack(pady=20)

        # Make it clickable and change the cursor
        link_label.bind("<Button-1>", lambda e: self.open_link(link_url))
        link_label.bind("<Enter>", lambda e: link_label.configure(cursor="hand2"))
        link_label.bind("<Leave>", lambda e: link_label.configure(cursor=""))

    def on_closing(self):
        self.grab_release()
        self.destroy()

class DictFlowApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DictFlow")

        self.history = TranscriptionHistory("transcription_history.json")
        self.text_enhancer = TextEnhancer("config.json")

        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        # Transparent window background so the rounded pill corners show through.
        # CTk paints the window via fg_color, so that must be the transparent key.
        self._bg_transparent = '#010101'
        try:
            self.root.configure(fg_color=self._bg_transparent)
        except Exception:
            pass
        try:
            self.root.configure(bg=self._bg_transparent)
        except Exception:
            pass
        try:
            self.root.attributes('-transparentcolor', self._bg_transparent)
        except Exception:
            self.root.attributes('-alpha', 0.95)

        self._pill_bg = '#161618'
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 36
        window_height = 142
        x = screen_width - window_width - 22
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.main_frame = ctk.CTkFrame(
            self.root, fg_color=self._pill_bg, corner_radius=16,
            border_width=1, border_color='#2A2A30'
        )
        self.main_frame.pack(fill='both', expand=True)

        # Context badge (top)
        self.mode_label = ctk.CTkLabel(
            self.main_frame, text="·", font=("Segoe UI", 9, "bold"),
            text_color='#7DD3FC', fg_color=self._pill_bg
        )
        self.mode_label.pack(pady=(12, 2))

        # Audio-reactive equalizer (center)
        self.eq_w, self.eq_h = 24, 54
        self.num_bars = 5
        self.bar_levels = [0.14] * self.num_bars
        self.current_level = 0.0
        self.canvas = tk.Canvas(
            self.main_frame, width=self.eq_w, height=self.eq_h,
            bg=self._pill_bg, highlightthickness=0, bd=0
        )
        self.canvas.pack(pady=2)

        # AI enhancement toggle (bottom) — sparkles, gold when on, dim when off.
        self.use_enhancer = ctk.BooleanVar(value=self.text_enhancer.enabled)
        self.ai_toggle = ctk.CTkLabel(
            self.main_frame, text="✨", font=("Segoe UI Emoji", 13),
            fg_color=self._pill_bg, text_color=self._ai_color()
        )
        self.ai_toggle.pack(pady=(6, 22))
        self.ai_toggle.bind("<Button-1>", self._on_ai_toggle_click)

        # Click the bar to start/stop recording (distinguished from a drag-to-move).
        self._press_x = 0
        self._press_y = 0

        # Tracks which monitor the bar is on, so it follows the active screen.
        self._current_monitor_key = None

        self.grabando = False
        self.frames = []
        self.ultima_pulsacion = 0
        self.DEBOUNCE_TIME = 0.5
        self.animacion_activa = False
        self.estado_actual = "inactivo"
        # Gate so the global hotkey toggles only once per physical press (the key
        # auto-repeat fires the callback many times while the combo is held).
        self._hotkeys = {}
        self._armed = {}
        self.modo = "dictado"
        self.hotkey = self.text_enhancer.get_hotkey()
        self.command_hotkey = self.text_enhancer.get_command_hotkey()
        self._registrar_hotkey('dict', self.hotkey, self.toggle_grabacion)
        self._registrar_hotkey('cmd', self.command_hotkey, self.toggle_comando, suppress=True)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.animar_puntos()
        self.setup_context_menu()
        self.settings_window = None

        # Variables and events for dragging the window
        self._offset_x = 0
        self._offset_y = 0
        for widget in [self.main_frame, self.mode_label, self.canvas]:
            widget.bind("<ButtonPress-1>", self.start_drag)
            widget.bind("<B1-Motion>", self.do_drag)
            widget.bind("<ButtonRelease-1>", self._on_bar_click)

        # Make the bar a non-activating window so clicking it never steals focus
        # from the app you are dictating into (otherwise the pasted text lands
        # nowhere). Windows-only, best-effort.
        self.root.after(200, self._make_no_activate)

    def _make_no_activate(self):
        try:
            import ctypes
            GWL_EXSTYLE = -20
            WS_EX_NOACTIVATE = 0x08000000
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.root.winfo_id()) or self.root.winfo_id()
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            if not (ex & WS_EX_NOACTIVATE):
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE)
                logging.info("Barra configurada como no-activable (no roba el foco).")
        except Exception as e:
            logging.warning(f"No se pudo aplicar NOACTIVATE: {e}")

    def start_drag(self, event):
        self._offset_x = event.x
        self._offset_y = event.y
        self._press_x = event.x_root
        self._press_y = event.y_root

    def do_drag(self, event):
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f"+{x}+{y}")

    def _on_bar_click(self, event=None):
        """A click on the bar (not a drag) toggles recording: gray=start, red=stop."""
        moved = (abs(event.x_root - self._press_x) + abs(event.y_root - self._press_y))
        if moved > 6:  # it was a drag to move the bar
            return
        if not self.grabando:
            logging.info("Iniciando grabación (clic en la barra)...")
            self.modo = "dictado"
            self.grabando = True
            threading.Thread(target=self.procesar_grabacion, daemon=True).start()
        else:
            logging.info("Deteniendo grabación (clic en la barra)...")
            self.grabando = False
            self.actualizar_estado("transcribiendo", True)

    def toggle_text_enhancer(self):
        self.text_enhancer.set_enabled(self.use_enhancer.get())

    def _ai_color(self):
        """Gold when AI enhancement is on, dim gray when off."""
        return '#FFD24A' if self.use_enhancer.get() else '#52525B'

    def _on_ai_toggle_click(self, event=None):
        self.use_enhancer.set(not self.use_enhancer.get())
        self.toggle_text_enhancer()
        try:
            self.ai_toggle.configure(text_color=self._ai_color())
        except Exception:
            pass

    def animar_puntos(self):
        """Drive the audio-reactive equalizer animation."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            estado = self.estado_actual if self.animacion_activa else "inactivo"
            if estado == "grabando":
                color = '#FF5A5A'
            elif estado == "transcribiendo":
                color = '#FFD24A'
            else:
                color = '#3C3C44'

            for i in range(self.num_bars):
                if estado == "grabando":
                    target = self.current_level * (0.55 + 0.9 * random.random())
                    target = max(0.1, min(1.0, target))
                elif estado == "transcribiendo":
                    target = 0.30 + 0.40 * (1 + math.sin(time.time() * 6 + i * 0.9)) / 2
                else:
                    target = 0.14 + 0.05 * (1 + math.sin(time.time() * 2.2 + i)) / 2
                self.bar_levels[i] += (target - self.bar_levels[i]) * 0.4

            self._draw_equalizer(color)
            if self.root.winfo_exists():
                self.root.after(45, self.animar_puntos)
        except Exception as e:
            logging.warning(f"Error en animar_puntos: {e}")

    def _draw_equalizer(self, color):
        """Render the vertical bars centered on the canvas with rounded caps."""
        if not hasattr(self, 'canvas') or not self.canvas.winfo_exists():
            return
        c = self.canvas
        c.delete("all")
        w, h = self.eq_w, self.eq_h
        cy = h / 2
        bw = 3
        gap = (w - self.num_bars * bw) / (self.num_bars + 1)
        for i in range(self.num_bars):
            x = gap + i * (bw + gap) + bw / 2
            bar_h = max(bw, self.bar_levels[i] * (h - 4))
            c.create_line(x, cy - bar_h / 2, x, cy + bar_h / 2,
                          fill=color, width=bw, capstyle='round')

    def actualizar_estado(self, estado, activar_animacion=True):
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            self.animacion_activa = activar_animacion
            self.estado_actual = estado
        except Exception as e:
            logging.warning(f"Error en actualizar_estado: {e}")

    # Short badges so context names fit the narrow vertical bar.
    _CONTEXT_BADGES = {
        "VS Code": "VS", "Cursor": "Cur", "Gmail": "Gm", "Correo": "Mail",
        "Slack": "Sl", "WhatsApp": "Wa", "Notion": "No", "Notas": "Nt",
    }

    def actualizar_contexto(self, contexto):
        """Show a short badge of the detected target application in the bar."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            texto = self._CONTEXT_BADGES.get(contexto, (contexto[:3] if contexto else "·"))
            self.mode_label.configure(text=texto)
        except Exception as e:
            logging.warning(f"Error en actualizar_contexto: {e}")

    def reubicar_en_monitor_activo(self, rect=None):
        """Move the bar to the monitor of the active window (multi-monitor).

        Only moves when the active monitor changed, so a manual drag within the
        same screen is respected.
        """
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        if rect is None:
            rect = get_active_monitor_work_area()
        if not rect:
            return
        left, top, right, bottom = rect
        key = (left, top)
        if key == self._current_monitor_key:
            return
        self._current_monitor_key = key
        try:
            w = self.root.winfo_width() or 36
            h = self.root.winfo_height() or 142
            x = right - w - 22
            y = top + ((bottom - top) - h) // 2
            self.root.geometry(f"+{x}+{y}")
        except Exception as e:
            logging.warning(f"No se pudo reubicar la barra: {e}")

    @staticmethod
    def _mensaje_fallo(error_msg):
        """Pick a friendly toast message: empty result vs. a real error."""
        if error_msg and any(k in error_msg for k in ("no devolvió", "válida", "valida")):
            return "🎤  No se detectó voz. Inténtalo de nuevo."
        return "⚠  No se pudo transcribir. Revisa tu API Key, cuota y conexión."

    def mostrar_toast(self, mensaje, ms=3500):
        """Show a sleek auto-dismissing notification beside the bar (no focus steal)."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
            return
        try:
            toast = ctk.CTkToplevel(self.root)
            toast.overrideredirect(True)
            toast.attributes('-topmost', True)
            # Transparent corners (rounded pill) like the main bar.
            try:
                toast.configure(fg_color='#010101')
                toast.attributes('-transparentcolor', '#010101')
                toast.attributes('-alpha', 0.97)
            except Exception:
                toast.attributes('-alpha', 0.95)

            frame = ctk.CTkFrame(toast, fg_color='#1E1E22', corner_radius=16,
                                 border_width=1, border_color='#3A3A42')
            frame.pack(fill='both', expand=True)
            ctk.CTkLabel(
                frame, text=mensaje, text_color='#F3F4F6',
                font=("Segoe UI", 11), wraplength=240, justify='left'
            ).pack(padx=16, pady=12)

            toast.update_idletasks()
            w, h = toast.winfo_width(), toast.winfo_height()
            bx, by = self.root.winfo_x(), self.root.winfo_y()
            bh = self.root.winfo_height()
            x = bx - w - 12            # to the left of the vertical bar
            y = by + (bh - h) // 2     # vertically centered with the bar
            # Clamp inside the active monitor so it is never cut off.
            rect = get_active_monitor_work_area()
            if rect:
                left, top, right, bottom = rect
                x = max(left + 8, min(x, right - w - 8))
                y = max(top + 8, min(y, bottom - h - 8))
            toast.geometry(f"+{x}+{y}")
            toast.after(ms, toast.destroy)
        except Exception as e:
            logging.warning(f"No se pudo mostrar el aviso: {e}")

    # --- Live (real-time) transcript preview ---

    def _show_live_preview(self):
        """Create the live-transcript preview window next to the bar."""
        if getattr(self, '_live_preview', None) and self._live_preview.winfo_exists():
            return
        try:
            self._live_preview = ctk.CTkToplevel(self.root)
            self._live_preview.overrideredirect(True)
            self._live_preview.attributes('-topmost', True)
            frame = ctk.CTkFrame(self._live_preview, fg_color="#161618",
                                 corner_radius=14, border_width=1, border_color="#2A2A30")
            frame.pack(fill="both", expand=True)
            self._live_label = ctk.CTkLabel(
                frame, text="Escuchando…", text_color="#E5E7EB",
                font=("Segoe UI", 12), wraplength=300, justify="left"
            )
            self._live_label.pack(padx=14, pady=10)
            self._position_live_preview()
        except Exception as e:
            logging.warning(f"No se pudo mostrar el preview en vivo: {e}")

    def _position_live_preview(self):
        try:
            self._live_preview.update_idletasks()
            w = self._live_preview.winfo_width()
            h = self._live_preview.winfo_height()
            x = self.root.winfo_x() - w - 12  # to the left of the vertical bar
            y = self.root.winfo_y() + (self.root.winfo_height() - h) // 2
            self._live_preview.geometry(f"+{max(8, x)}+{max(8, y)}")
        except Exception:
            pass

    def _update_live_preview(self, text):
        try:
            if getattr(self, '_live_preview', None) and self._live_preview.winfo_exists():
                self._live_label.configure(text=text or "Escuchando…")
                self._position_live_preview()
        except Exception:
            pass

    def _hide_live_preview(self):
        try:
            if getattr(self, '_live_preview', None) and self._live_preview.winfo_exists():
                self._live_preview.destroy()
        except Exception:
            pass
        self._live_preview = None

    @staticmethod
    def _audio_level(chunk_bytes):
        """Approximate normalized RMS level (0..1) of an int16 PCM chunk."""
        try:
            samples = array.array('h')
            samples.frombytes(chunk_bytes)
            if not samples:
                return 0.0
            rms = math.sqrt(sum(s * s for s in samples) / len(samples))
            return max(0.0, min(1.0, rms / 6000.0))
        except Exception:
            return 0.0

    @staticmethod
    def listar_microfonos():
        """List selectable input devices (MME host API, friendly names)."""
        mics = []
        try:
            for i, d in enumerate(sd.query_devices()):
                ha = sd.query_hostapis(d['hostapi'])['name']
                if d['max_input_channels'] > 0 and ha == 'MME' and 'Sound Mapper' not in d['name']:
                    mics.append((i, d['name']))
        except Exception as e:
            logging.warning(f"No se pudieron listar micrófonos: {e}")
        return mics

    def _resolve_input_device(self):
        """Resolve the configured mic name to a device index (None = default)."""
        name = self.text_enhancer.get_input_device_name()
        if not name:
            return None
        try:
            for i, d in enumerate(sd.query_devices()):
                if d['max_input_channels'] > 0 and d['name'] == name:
                    return i
        except Exception:
            pass
        return None

    def grabar_audio(self):
        logging.info("Iniciando grabación de audio")
        stream = None
        try:
            # A fresh stream per recording (reusing one across recordings
            # captured silence on some devices).
            stream = sd.RawInputStream(
                samplerate=RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK,
                device=self._resolve_input_device()
            )
            stream.start()
            self.actualizar_estado("grabando", True)
            self._beep(start=True)
            self.frames = []
            logging.info("Iniciando captura de frames de audio")
            auto_stop = self.text_enhancer.get_auto_stop_silence()
            sil_limit = self.text_enhancer.get_silence_seconds()
            chunk_dur = CHUNK / RATE
            silence_run = 0.0
            spoke = False
            while self.grabando:
                data, overflowed = stream.read(CHUNK)
                if overflowed:
                    logging.warning("Desbordamiento del buffer de audio (overflow).")
                chunk_bytes = bytes(data)
                self.frames.append(chunk_bytes)
                lvl = self._audio_level(chunk_bytes)
                self.current_level = lvl
                # Auto-stop: end the recording after a run of silence once the
                # user has actually started speaking.
                if lvl > 0.04:
                    spoke = True
                    silence_run = 0.0
                elif spoke:
                    silence_run += chunk_dur
                    if auto_stop and silence_run >= sil_limit:
                        logging.info("Auto-stop por silencio.")
                        self.grabando = False
                        self.root.after(0, self.actualizar_estado, "transcribiendo", True)

            # Capture a short tail so the last words are not clipped (there is
            # latency between speaking and the audio reaching the buffer).
            for _ in range(int(0.45 * RATE / CHUNK)):
                try:
                    data, _of = stream.read(CHUNK)
                    self.frames.append(bytes(data))
                except Exception:
                    break

            self.current_level = 0.0
            self._beep(start=False)
            logging.info("Grabación detenida.")
        except Exception as e:
            logging.error(f"Error durante la grabación: {e}")
            return None
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

        if not self.frames:
            logging.warning("No se capturaron frames de audio.")
            return None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                wf = wave.open(temp_file.name, 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(SAMPLE_WIDTH)
                wf.setframerate(RATE)
                wf.writeframes(b''.join(self.frames))
                wf.close()
                logging.info(f"Audio guardado en: {temp_file.name}")
                return temp_file.name
        except Exception as e:
            logging.error(f"Error al guardar archivo WAV: {e}")
            return None

    def pegar_texto(self, texto):
        if texto:
            pyperclip.copy(texto)
            keyboard.send('ctrl+v')
            self.actualizar_estado("inactivo", False)

    def _beep(self, start=True):
        """Subtle audio cue on start/stop of recording (Windows)."""
        if not self.text_enhancer.get_sound_feedback():
            return

        def play():
            try:
                import winsound
                winsound.Beep(900 if start else 560, 80)
            except Exception:
                pass

        threading.Thread(target=play, daemon=True).start()

    # --- Voice command on selected text ---

    def _capturar_seleccion(self):
        """Copy the current selection from the focused app; return (old_clip, selection)."""
        old = ""
        try:
            old = pyperclip.paste()
        except Exception:
            pass
        sel = ""
        try:
            # Wait until the user releases the hotkey modifiers, otherwise the
            # Ctrl+C is interpreted as Ctrl+Shift+C and nothing is copied.
            t0 = time.time()
            while time.time() - t0 < 1.5:
                if not (keyboard.is_pressed('ctrl') or keyboard.is_pressed('shift')
                        or keyboard.is_pressed('alt')):
                    break
                time.sleep(0.03)
            time.sleep(0.06)
            pyperclip.copy('')  # clear so we can tell if the copy actually worked
            keyboard.send('ctrl+c')
            time.sleep(0.22)  # let the copy land
            sel = pyperclip.paste()
        except Exception as e:
            logging.error(f"Error capturando selección: {e}")
        logging.info(f"Comando: selección capturada ({len(sel or '')} chars)")
        return old, sel

    def _restaurar_clip(self, old):
        if old:
            try:
                pyperclip.copy(old)
            except Exception:
                pass

    def _pegar_y_restaurar(self, result, old_clip):
        pyperclip.copy(result)
        keyboard.send('ctrl+v')
        if old_clip:
            self.root.after(400, lambda: self._restaurar_clip(old_clip))
        self.actualizar_estado("inactivo", False)

    def procesar_comando(self):
        if not self.text_enhancer.is_configured:
            self.root.after(0, self.show_api_warning_window)
            self.grabando = False
            self.actualizar_estado("inactivo", False)
            return

        old_clip, selected = self._capturar_seleccion()
        if not selected.strip():
            self.grabando = False
            self.root.after(0, self.mostrar_toast, "⚠  Selecciona primero el texto a transformar.")
            self.actualizar_estado("inactivo", False)
            self._restaurar_clip(old_clip)
            return

        self.root.after(0, self.actualizar_contexto, "CMD")
        audio_file = self.grabar_audio()
        if not audio_file:
            self.actualizar_estado("inactivo", False)
            self._restaurar_clip(old_clip)
            return

        error = None
        result = None
        try:
            logging.info(f"Transformando texto seleccionado por voz... (sel={selected[:50]!r})")
            result = self.text_enhancer.transform_with_audio(selected, audio_file)
            logging.info(f"Comando: resultado ({len(result or '')} chars): {(result or '')[:60]!r}")
        except Exception as e:
            error = str(e)
            logging.error(f"Error en comando de voz: {e}")
        try:
            os.unlink(audio_file)
        except Exception:
            pass

        if error or not result or not result.strip():
            self.root.after(0, self.mostrar_toast, "⚠  No se pudo transformar el texto.")
            self._restaurar_clip(old_clip)
            self.actualizar_estado("inactivo", False)
        else:
            self.history.add_transcription(result, 0.0, True, "command")
            self.root.after(0, self._pegar_y_restaurar, result, old_clip)

    def _rearm(self, name):
        """Re-arm a hotkey once its trigger key is released (ignores auto-repeat)."""
        self._armed[name] = True

    def _registrar_hotkey(self, name, hotkey, callback, suppress=False):
        """(Re)register a named global hotkey and its auto-repeat re-arm hook.

        suppress=True blocks the combo from reaching other apps (so a command
        hotkey can reuse a key that an app like VS Code also binds).
        """
        old = self._hotkeys.get(name)
        if old:
            try:
                keyboard.remove_hotkey(old['hotkey'])
            except Exception:
                pass
            try:
                keyboard.unhook(old['release'])
            except Exception:
                pass
        self._armed[name] = True
        try:
            keyboard.add_hotkey(hotkey, callback, suppress=suppress)
        except Exception:
            keyboard.add_hotkey(hotkey, callback)
        trigger_key = hotkey.split('+')[-1].strip()
        release = keyboard.on_release_key(trigger_key, lambda e, n=name: self._rearm(n))
        self._hotkeys[name] = {'hotkey': hotkey, 'release': release}
        logging.info(f"Atajo '{name}' registrado: {hotkey}")

    def cambiar_hotkey(self, nuevo_hotkey: str) -> bool:
        """Validate, apply and persist a new dictation hotkey."""
        nuevo_hotkey = (nuevo_hotkey or "").strip().lower()
        if not nuevo_hotkey:
            return False
        try:
            keyboard.parse_hotkey(nuevo_hotkey)
        except Exception:
            logging.error(f"Atajo inválido: {nuevo_hotkey}")
            return False
        try:
            self.hotkey = nuevo_hotkey
            self._registrar_hotkey('dict', nuevo_hotkey, self.toggle_grabacion)
            self.text_enhancer.set_hotkey(nuevo_hotkey)
            return True
        except Exception as e:
            logging.error(f"No se pudo cambiar el atajo: {e}")
            return False

    def cambiar_command_hotkey(self, nuevo_hotkey: str) -> bool:
        """Validate, apply and persist a new command (transform) hotkey."""
        nuevo_hotkey = (nuevo_hotkey or "").strip().lower()
        if not nuevo_hotkey:
            return False
        try:
            keyboard.parse_hotkey(nuevo_hotkey)
        except Exception:
            logging.error(f"Atajo inválido: {nuevo_hotkey}")
            return False
        try:
            self.command_hotkey = nuevo_hotkey
            self._registrar_hotkey('cmd', nuevo_hotkey, self.toggle_comando, suppress=True)
            self.text_enhancer.set_command_hotkey(nuevo_hotkey)
            return True
        except Exception as e:
            logging.error(f"No se pudo cambiar el atajo de comando: {e}")
            return False

    def toggle_grabacion(self):
        if not self._armed.get('dict', True):
            return
        self._armed['dict'] = False
        tiempo_actual = time.time()
        if tiempo_actual - self.ultima_pulsacion < self.DEBOUNCE_TIME:
            return
        self.ultima_pulsacion = tiempo_actual
        if not self.grabando:
            logging.info("Iniciando grabación...")
            self.modo = "dictado"
            self.grabando = True
            threading.Thread(target=self.procesar_grabacion, daemon=True).start()
        elif self.modo == "dictado":
            logging.info("Deteniendo grabación...")
            self.grabando = False
            self.actualizar_estado("transcribiendo", True)

    def toggle_comando(self):
        if not self._armed.get('cmd', True):
            return
        self._armed['cmd'] = False
        tiempo_actual = time.time()
        if tiempo_actual - self.ultima_pulsacion < self.DEBOUNCE_TIME:
            return
        self.ultima_pulsacion = tiempo_actual
        if not self.grabando:
            logging.info("Iniciando comando de voz...")
            self.modo = "comando"
            self.grabando = True
            threading.Thread(target=self.procesar_comando, daemon=True).start()
        elif self.modo == "comando":
            logging.info("Deteniendo comando de voz...")
            self.grabando = False
            self.actualizar_estado("transcribiendo", True)

    def procesar_grabacion(self):
        if not self.text_enhancer.is_configured:
            logging.error("API de Gemini no configurada. Abortando transcripción.")
            self.root.after(0, self.show_api_warning_window)
            self.actualizar_estado("inactivo", False)
            return

        # Detect the focused application (UI Automation) so the pipeline can
        # adapt the style to where the text will be pasted (Slack, Gmail, ...).
        contexto = detect_context()
        logging.info(f"Contexto detectado: {contexto}")
        self.root.after(0, self.actualizar_contexto, contexto)

        # Move the bar to the monitor where the active window lives (captured
        # here, while the target app is still in the foreground).
        monitor_rect = get_active_monitor_work_area()
        self.root.after(0, self.reubicar_en_monitor_activo, monitor_rect)

        if self.text_enhancer.get_realtime_mode():
            self._procesar_realtime(contexto)
        else:
            self._procesar_batch(contexto)

        self.actualizar_estado("inactivo", False)

    def _procesar_batch(self, contexto):
        """Record fully, then transcribe + refine in a single Gemini call."""
        tiempo_inicio = time.time()
        audio_file = self.grabar_audio()

        if not audio_file:
            logging.warning("No se generó archivo de audio para transcribir.")
            return

        texto_final = ""
        used_gemini = False
        error_msg = None
        try:
            aplicar_mejora = self.use_enhancer.get()
            if aplicar_mejora:
                logging.info("Transcribiendo y refinando texto...")
            texto_final = self.text_enhancer.transcribe_audio(
                audio_file, context=contexto, enhance=aplicar_mejora
            )
            used_gemini = True
        except Exception as e:
            logging.error(f"Error en la transcripción con Gemini: {e}")
            error_msg = str(e)

        if error_msg or not texto_final.strip():
            self.root.after(0, self.mostrar_toast, self._mensaje_fallo(error_msg))
        else:
            duracion = time.time() - tiempo_inicio
            self.history.add_transcription(texto_final, duracion, used_gemini, "gemini_only")
            self.root.after(0, self.pegar_texto, texto_final)

        try:
            os.unlink(audio_file)
            logging.info(f"Archivo temporal {audio_file} eliminado.")
        except Exception as e:
            logging.error(f"Error al eliminar archivo temporal: {e}")

    def _procesar_realtime(self, contexto):
        """Stream audio to the Live API and show the transcript while speaking."""
        try:
            from live_transcriber import LiveTranscriber
        except Exception as e:
            logging.error(f"Live no disponible, usando batch: {e}")
            self._procesar_batch(contexto)
            return

        self._live_text = ""

        def on_text(piece):
            self._live_text += piece
            self.root.after(0, self._update_live_preview, self._live_text)

        lt = LiveTranscriber(
            self.text_enhancer.api_key,
            self.text_enhancer.get_live_system_instruction(contexto),
            on_text=on_text,
        )
        self.root.after(0, self._show_live_preview)
        lt.start()

        self.actualizar_estado("grabando", True)
        self._grabar_streaming(lt)
        raw = lt.stop()
        self.root.after(0, self._hide_live_preview)

        if lt.error:
            logging.error(f"Live error: {lt.error}")
            self.root.after(0, self.mostrar_toast, "⚠  Error en tiempo real. Revisa tu conexión.")
            return
        if not raw.strip():
            self.root.after(0, self.mostrar_toast, "🎤  No se detectó voz. Inténtalo de nuevo.")
            return

        # Refine the raw real-time transcript with the usual pipeline.
        final = raw
        if self.use_enhancer.get():
            try:
                final = self.text_enhancer.enhance_text(raw, context=contexto)
            except Exception as e:
                logging.error(f"Error al refinar (live): {e}")
                final = raw

        self.history.add_transcription(final, 0.0, True, "gemini_live")
        self.root.after(0, self.pegar_texto, final)

    def _grabar_streaming(self, lt):
        """Recording loop that feeds chunks to the Live transcriber (no WAV)."""
        logging.info("Iniciando grabación en tiempo real")
        stream = None
        try:
            stream = sd.RawInputStream(
                samplerate=RATE, channels=CHANNELS, dtype='int16', blocksize=CHUNK,
                device=self._resolve_input_device()
            )
            stream.start()
            while self.grabando:
                data, overflowed = stream.read(CHUNK)
                if overflowed:
                    logging.warning("Desbordamiento del buffer de audio (overflow, live).")
                chunk = bytes(data)
                self.current_level = self._audio_level(chunk)
                lt.feed(chunk)
            self.current_level = 0.0
            logging.info("Grabación en tiempo real detenida.")
        except Exception as e:
            logging.error(f"Error durante la grabación en tiempo real: {e}")
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

    def show_error_message(self, message):
        messagebox.showerror("Error", message)

    def show_api_warning_window(self):
        if hasattr(self, 'api_warning_window') and self.api_warning_window.winfo_exists():
            self.api_warning_window.lift()
            self.api_warning_window.focus_force()
            return

        self.api_warning_window = ctk.CTkToplevel(self.root)
        self.api_warning_window.title("Advertencia")
        self.api_warning_window.attributes('-topmost', True)
        self.api_warning_window.configure(fg_color="#2C2C2C")
        self.api_warning_window.protocol("WM_DELETE_WINDOW", self.api_warning_window.destroy)
        self.api_warning_window.resizable(False, False)

        WIN_WIDTH = 400

        label = ctk.CTkLabel(
            self.api_warning_window,
            text="Tienes que poner la API para poder grabar. Cierra esta ventana, haz clic derecho en el programa y selecciona 'Configuración' para pegar tu clave API.",
            wraplength=WIN_WIDTH - 20,
            fg_color="transparent",
            text_color="#FFCC00",
            font=("Arial", 10),
            justify="center"
        )
        label.pack(padx=10, pady=10, fill="x", expand=True)

        self.api_warning_window.update_idletasks()

        win_height = self.api_warning_window.winfo_height()

        main_win_x = self.root.winfo_x()
        main_win_y = self.root.winfo_y()
        main_win_width = self.root.winfo_width()

        x = main_win_x + (main_win_width - WIN_WIDTH) // 2
        y = main_win_y - win_height

        self.api_warning_window.geometry(f'{WIN_WIDTH}x{win_height}+{x}+{y}')
        self.api_warning_window.grab_set()

    def on_closing(self):
        try:
            logging.info("Cerrando la aplicación...")
            self.grabando = False
            self.animacion_activa = False
            for hk in getattr(self, '_hotkeys', {}).values():
                try:
                    keyboard.remove_hotkey(hk['hotkey'])
                except Exception:
                    pass
                try:
                    keyboard.unhook(hk['release'])
                except Exception:
                    pass

            if self.settings_window and self.settings_window.winfo_exists():
                self.settings_window.destroy()

            self.text_enhancer._save_config()
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            logging.error(f"Error durante el cierre: {e}")
        finally:
            os._exit(0)

    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Configuración", command=self.show_settings)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Salir", command=self.on_closing)

        for widget in [self.root, self.main_frame, self.mode_label, self.canvas, self.ai_toggle]:
            widget.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        self.context_menu.post(event.x_root, event.y_root)

    def show_settings(self):
        if self.settings_window is None or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self.root, self.history, self.text_enhancer, self)
        self.settings_window.deiconify()
        self.settings_window.lift()
        self.settings_window.focus_force()

def ensure_single_instance():
    """Acquire a Windows named mutex so only one DictFlow runs at a time.

    Returns the mutex handle (kept open for the process lifetime) if this is the
    only instance, None if another instance already holds it, or True when the
    guard cannot run (non-Windows / error) so the app is never blocked wrongly.
    """
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        ERROR_ALREADY_EXISTS = 183
        handle = kernel32.CreateMutexW(None, False, "DictFlow_SingleInstance_Mutex")
        if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            return None
        return handle
    except Exception as e:
        logging.warning(f"No se pudo verificar instancia única: {e}")
        return True  # fail open: never block the app because of the guard


def main():
    # Single-instance guard: stop immediately (non-blocking) if DictFlow is
    # already running, so a duplicate/auto-spawned process never lingers.
    instance_lock = ensure_single_instance()
    if instance_lock is None:
        logging.warning("DictFlow ya se está ejecutando; cerrando esta instancia.")
        return

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    app = DictFlowApp(root)
    root.mainloop()
    # Keep a reference so the mutex handle lives until the app closes.
    del instance_lock

if __name__ == "__main__":
    main()
