"""Speech in and out. Both parts are optional and imported lazily, so Vision
still works in text mode when the audio packages are not installed."""

from __future__ import annotations


class SpeechUnavailable(RuntimeError):
    pass


class Speaker:
    """Text to speech using the offline pyttsx3 engine."""

    def __init__(self, rate: int = 180):
        try:
            import pyttsx3
        except ImportError as err:
            raise SpeechUnavailable("Install pyttsx3 for spoken replies.") from err
        try:
            self.engine = pyttsx3.init()
        except Exception as err:
            raise SpeechUnavailable(f"No speech engine available: {err}") from err
        self.engine.setProperty("rate", rate)

    def say(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


class Listener:
    """Speech to text from the microphone using the SpeechRecognition package."""

    def __init__(self, language: str = "en-US"):
        try:
            import speech_recognition as sr
        except ImportError as err:
            raise SpeechUnavailable("Install SpeechRecognition and PyAudio to use the microphone.") from err
        self.sr = sr
        self.language = language
        self.recognizer = sr.Recognizer()
        try:
            self.microphone = sr.Microphone()
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
        except Exception as err:
            raise SpeechUnavailable(f"No microphone available: {err}") from err

    def listen(self, timeout: float | None = None, phrase_limit: float = 15) -> str | None:
        """Return what was heard, or None if nothing was understood."""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_limit
                )
            return self.recognizer.recognize_google(audio, language=self.language)
        except (self.sr.WaitTimeoutError, self.sr.UnknownValueError):
            return None
        except self.sr.RequestError as err:
            raise SpeechUnavailable(f"Speech recognition service failed: {err}") from err


def strip_wake_word(heard: str, wake_word: str) -> str | None:
    """Return the request that follows the wake word, or None if it was not said.

    "hey vision what time is it" -> "what time is it"
    "vision"                     -> ""   (woken with no request yet)
    """
    words = heard.strip().split()
    lowered = [w.lower().strip(",.!?") for w in words]
    if wake_word not in lowered:
        return None
    index = lowered.index(wake_word)
    return " ".join(words[index + 1:]).strip()
