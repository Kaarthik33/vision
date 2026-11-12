# Vision

Vision is a voice assistant for your computer. Say "Vision", ask for something, and it answers out loud. Behind the voice is a language model of your choice (Claude, OpenAI, Gemini, or a free local model through Ollama) that can use tools to get things done: check the weather, look things up, do maths, open apps and websites, read and write files, run commands, and remember notes between sessions.

```
You:    Vision, what's the weather in Berlin?
          [tool] weather {'city': 'Berlin'}
Vision: It's partly cloudy in Berlin, about 9 degrees with a light wind.

You:    Vision, remember that my project demo is on Friday.
          [tool] remember {'note': 'Project demo is on Friday'}
Vision: Got it, I'll remember that.
```

## Quick start

Vision needs Python 3.10 or newer. The core has no third-party dependencies.

```bash
git clone https://github.com/Kaarthik33/vision.git
cd vision
cp .env.example .env        # then choose a provider and add its key
python -m vision --text     # typing mode, works straight away
```

For the voice features, install the audio packages and start without `--text`:

```bash
pip install -r requirements.txt
python -m vision
```

If the microphone or speech packages are missing, Vision says so and falls back to typing instead of failing.

> PyAudio needs the PortAudio library. On Windows, `pip install PyAudio` is enough. On macOS run `brew install portaudio` first, and on Debian/Ubuntu `sudo apt install portaudio19-dev espeak-ng`.

## Choosing a model

Set `VISION_PROVIDER` in `.env` (or pass `--provider`). Only the key for the provider you use is needed.

| Provider    | Key variable        | Default model       | Notes                                   |
|-------------|---------------------|---------------------|-----------------------------------------|
| `ollama`    | none                | `llama3.1`          | Free and local. Install [Ollama](https://ollama.com), then `ollama pull llama3.1`. |
| `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` | Claude                                  |
| `openai`    | `OPENAI_API_KEY`    | `gpt-4o-mini`       |                                         |
| `gemini`    | `GEMINI_API_KEY`    | `gemini-2.5-flash`  | Uses Gemini's OpenAI-compatible endpoint |

Model names change over time. Override the default with `VISION_MODEL` or `--model`. With Ollama, pick a model that supports tool calling.

## Usage

```bash
python -m vision                      # voice mode, wake word "vision"
python -m vision --no-wake            # respond to everything it hears
python -m vision --text               # type instead of speaking
python -m vision --text --mute        # type, and don't speak replies
python -m vision --once "what is 15% of 240"
python -m vision --provider anthropic --model claude-sonnet-4-5
python -m vision --list-tools
```

Say or type "goodbye" or "exit" to quit.

## Built-in tools

| Tool           | What it does                                   |
|----------------|------------------------------------------------|
| `get_time`     | Current date and time                          |
| `calculate`    | Safe maths evaluation (no `eval`)              |
| `weather`      | Current weather for a city (Open-Meteo, no key) |
| `wikipedia`    | Short summary of a topic                       |
| `web_search`   | Opens a search in your browser                 |
| `open_website` | Opens a URL in your browser                    |
| `open_app`     | Launches an application                        |
| `system_info`  | OS, Python version, free disk space            |
| `read_file`, `list_files` | Read a text file, list a folder     |
| `write_file`   | Create or overwrite a file (asks first)        |
| `run_command`  | Run a shell command (asks first)               |
| `remember`, `recall` | Notes saved in `~/.vision/memory.json`   |

### Safety

`write_file` and `run_command` can change your computer, so Vision asks for a yes before each use. Anything other than a clear yes is treated as no. The `--yes` flag turns the question off; only use it if you trust what you are asking for.

## Adding your own tool

A tool is a Python function plus a description the model reads. Add it in any file under `vision/tools/` inside that file's `register` function:

```python
@registry.register(
    "roll_dice",
    "Roll a dice with the given number of sides.",
    {"sides": {"type": "integer"}},
    ["sides"],
)
def roll_dice(sides):
    import random
    return random.randint(1, sides)
```

The model will start using it the next time Vision runs. Pass `dangerous=True` for tools that should ask for confirmation.

## How it works

```
microphone -> speech to text -> wake word -> Assistant -> text to speech -> speaker
                                                |
                                     language model provider
                                                |
                                        tool calls and results
```

- `vision/assistant.py` holds the loop: send the conversation to the model, run any tools it asks for, feed the results back, repeat until it gives a spoken answer.
- `vision/providers/` adapts that loop to each model API. One class covers OpenAI, Gemini and Ollama; another covers Claude.
- `vision/tools/` contains the tool registry and built-in tools.
- `vision/speech.py` wraps the microphone and the offline text-to-speech engine.
- `vision/cli.py` ties it together.

Speech recognition uses Google's free web recognizer through the SpeechRecognition package, so audio after the microphone picks up speech is sent to that service. Text to speech runs offline.

## Tests

```bash
pip install pytest
python -m pytest
```

The tests run offline with a scripted fake model, so they need no API key, network or microphone.

## Limits

Vision is a general assistant, not a magic one: it can do what its tools and the chosen model allow. Small local models make more tool-calling mistakes than the larger hosted ones, and voice recognition needs an internet connection.

## License

MIT © 2026 Kaarthic Pranav Thirumurthy
