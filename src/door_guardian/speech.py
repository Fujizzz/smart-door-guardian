"""Optional offline text-to-speech support."""

from __future__ import annotations


class Speaker:
    def __init__(self) -> None:
        self._engine = None

    def available(self) -> bool:
        try:
            import pyttsx3  # type: ignore
        except ImportError:
            return False
        if self._engine is None:
            self._engine = pyttsx3.init()
        return True

    def speak(self, text: str) -> bool:
        if not self.available():
            print(f"[语音提示] {text}")
            return False
        self._engine.say(text)
        self._engine.runAndWait()
        return True

