"""Command line entry point: `python -m vision`."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .assistant import Assistant
from .config import DEFAULT_MODELS, Config
from .providers import ProviderError, create_provider
from .speech import Listener, Speaker, SpeechUnavailable, strip_wake_word
from .tools import build_registry

EXIT_WORDS = {"exit", "quit", "goodbye", "bye", "stop listening", "shut down"}
YES_WORDS = {"yes", "y", "yeah", "yep", "sure", "ok", "okay", "allow", "do it", "go ahead"}


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="vision", description="Vision, a voice AI assistant.")
    parser.add_argument("--text", action="store_true", help="type instead of using the microphone")
    parser.add_argument("--once", metavar="REQUEST", help="answer a single request and exit")
    parser.add_argument("--provider", choices=sorted(DEFAULT_MODELS), help="language model provider")
    parser.add_argument("--model", help="model name for the chosen provider")
    parser.add_argument("--no-wake", action="store_true", help="respond to everything heard, without the wake word")
    parser.add_argument("--mute", action="store_true", help="do not speak replies aloud")
    parser.add_argument("--yes", action="store_true", help="allow commands and file writes without asking")
    parser.add_argument("--list-tools", action="store_true", help="show the built-in tools and exit")
    parser.add_argument("--version", action="version", version=f"vision {__version__}")
    return parser.parse_args(argv)


def build_config(args) -> Config:
    config = Config.from_env()
    if args.provider and args.provider != config.provider:
        import os
        from .config import API_KEY_VARS

        config.provider = args.provider
        config.model = DEFAULT_MODELS[args.provider]
        var = API_KEY_VARS[args.provider]
        config.api_key = os.environ.get(var, "") if var else ""
    if args.model:
        config.model = args.model
    config.use_wake_word = not args.no_wake
    config.auto_approve = args.yes
    return config


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        config = build_config(args)
    except ValueError as err:
        print(f"Configuration error: {err}", file=sys.stderr)
        return 2
    tools = build_registry(config)

    if args.list_tools:
        for name in tools.names():
            tool = tools.get(name)
            flag = "  (asks first)" if tool.dangerous else ""
            print(f"{name:14} {tool.description}{flag}")
        return 0

    try:
        provider = create_provider(config)
    except ProviderError as err:
        print(f"Setup error: {err}", file=sys.stderr)
        return 2

    speaker = None
    if not args.mute and not args.once:
        try:
            speaker = Speaker(config.voice_rate)
        except SpeechUnavailable as err:
            print(f"[voice output off: {err}]")

    listener = None
    if not args.text and not args.once:
        try:
            listener = Listener(config.language)
        except SpeechUnavailable as err:
            print(f"[microphone off, switching to typing: {err}]")

    def say(text: str) -> None:
        print(f"Vision: {text}")
        if speaker:
            speaker.say(text)

    def confirm(question: str) -> bool:
        if listener:
            say(question + " Say yes or no.")
            answer = listener.listen(timeout=8) or ""
        else:
            answer = input(f"{question} [y/N] ")
        return answer.strip().lower() in YES_WORDS

    assistant = Assistant(
        provider, tools, config, confirm=confirm,
        on_tool=lambda name, a: print(f"  [tool] {name} {a}"),
    )

    def respond(request: str) -> bool:
        """Handle one request. Returns False when the user wants to leave."""
        if request.lower().strip(" .!") in EXIT_WORDS:
            say("Goodbye.")
            return False
        try:
            say(assistant.ask(request))
        except ProviderError as err:
            say(f"I could not reach the language model. {err}")
        return True

    if args.once:
        respond(args.once)
        return 0

    print(f"Vision {__version__} using {config.provider} ({config.model}). Ctrl+C to quit.")
    try:
        if listener:
            return voice_loop(listener, config, say, respond)
        return text_loop(respond)
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        return 0


def text_loop(respond) -> int:
    while True:
        request = input("You: ").strip()
        if request and not respond(request):
            return 0


def voice_loop(listener, config, say, respond) -> int:
    hint = f"Say '{config.wake_word}' followed by your request." if config.use_wake_word else "I'm listening."
    say(f"Vision is ready. {hint}")
    while True:
        heard = listener.listen()
        if not heard:
            continue
        if config.use_wake_word:
            request = strip_wake_word(heard, config.wake_word)
            if request is None:
                continue
            if not request:
                say("Yes?")
                request = listener.listen(timeout=8) or ""
                if not request:
                    continue
        else:
            request = heard
        print(f"You: {request}")
        if not respond(request):
            return 0
