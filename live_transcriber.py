"""Real-time transcription via the Gemini Live API (experimental).

Streams microphone audio chunks to the Live API over a WebSocket and emits the
transcribed/refined text as it arrives, so the user sees text while speaking.

Runs its own asyncio event loop in a background thread; audio chunks are pushed
in from the recording thread via feed(), and incremental text is delivered
through the on_text callback (called from the asyncio thread).
"""
import asyncio
import logging
import queue
import threading

from google import genai
from google.genai import types

# Live-capable model for the Gemini Developer API (API-key auth). Must support
# the bidiGenerateContent action; list them with client.models.list().
LIVE_MODEL = "gemini-3.1-flash-live-preview"

# Live audio must be raw PCM; we record 16-bit mono at 16 kHz.
AUDIO_MIME = "audio/pcm;rate=16000"


class LiveTranscriber:
    def __init__(self, api_key, system_instruction, on_text=None, model=LIVE_MODEL):
        self.api_key = api_key
        self.system_instruction = system_instruction
        self.on_text = on_text          # called with each incremental text chunk
        self.model = model
        self._audio_q = queue.Queue()
        self._thread = None
        self._running = False
        self._audio_ended = False
        self._text_parts = []
        self._done = threading.Event()
        self.error = None

    def start(self):
        """Open the Live session and begin streaming in a background thread."""
        self._running = True
        self._audio_ended = False
        self._text_parts = []
        self.error = None
        self._done.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def feed(self, audio_chunk: bytes):
        """Push a raw PCM audio chunk to be streamed to the model."""
        if self._running:
            self._audio_q.put(audio_chunk)

    def stop(self, timeout=20) -> str:
        """Signal end of audio, wait for the final transcript and return it."""
        self._running = False
        self._audio_q.put(None)  # sentinel: end of audio
        self._done.wait(timeout=timeout)
        return "".join(self._text_parts).strip()

    # --- internals (asyncio thread) ---

    def _run(self):
        try:
            asyncio.run(self._session())
        except Exception as e:
            self.error = str(e)
            logging.error(f"Live transcriber error: {e}")
        finally:
            self._done.set()

    async def _session(self):
        client = genai.Client(api_key=self.api_key)
        # These Live models output audio; we don't use the audio reply. We only
        # read the transcription of the *input* audio (what the user dictates).
        config = {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": {},
        }
        async with client.aio.live.connect(model=self.model, config=config) as session:
            sender = asyncio.create_task(self._send_audio(session))
            try:
                async for msg in session.receive():
                    sc = getattr(msg, "server_content", None)
                    if sc is not None:
                        it = getattr(sc, "input_transcription", None)
                        text = getattr(it, "text", None) if it else None
                        if text:
                            self._text_parts.append(text)
                            if self.on_text:
                                try:
                                    self.on_text(text)
                                except Exception:
                                    pass
                        if getattr(sc, "turn_complete", False) and self._audio_ended:
                            break
            finally:
                sender.cancel()
                try:
                    await sender
                except (asyncio.CancelledError, Exception):
                    pass

    async def _send_audio(self, session):
        loop = asyncio.get_event_loop()
        while True:
            chunk = await loop.run_in_executor(None, self._audio_q.get)
            if chunk is None:
                self._audio_ended = True
                try:
                    await session.send_realtime_input(audio_stream_end=True)
                except Exception as e:
                    logging.error(f"Error ending live audio stream: {e}")
                return
            try:
                await session.send_realtime_input(
                    audio=types.Blob(data=chunk, mime_type=AUDIO_MIME)
                )
            except Exception as e:
                logging.error(f"Error sending live audio: {e}")
                return
