# mlx-tts

TOML-driven TTS wrapper for [mlx-audio](https://github.com/Blaizzy/mlx-audio) on Apple Silicon.

## Requirements

- Python 3.11+ (or 3.8+ with `pip install tomli`)
- [mlx-audio](https://github.com/Blaizzy/mlx-audio)
- soundfile

```
pip install mlx-audio soundfile
```

## Usage

```
python mlx_tts.py config.toml
python mlx_tts.py config.toml --dry-run
```

Output paths are derived automatically from the TOML filename:

| TOML | Output |
|------|--------|
| `[script]` | `./<stem>.<format>` |
| `[[script]]` | `./<stem>/<stem>_000.<format>`, `<stem>_001.<format>`, … |

## TOML format

### Minimal

```toml
model = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

[script]
text = "Hello, world."
```

### Full (single text)

```toml
format = "wav"   # wav | flac | mp3  (default: wav)
model  = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

[params]
# Passed directly to model.generate() — any key the model accepts is valid.
voice       = "Ryan"
lang_code   = "auto"
speed       = 1.0
temperature = 0.9

[script]
text = """
Hello, world. This is a test.
"""
```

### Multiple texts

```toml
format = "wav"
model  = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

[params]
lang_code   = "auto"
temperature = 0.9

[[script]]
text  = "Hello, my name is Ryan."
voice = "Ryan"

[[script]]
text  = "And I am Vivian. Nice to meet you!"
voice = "Vivian"
```

`[params]` provides global defaults. Any key in a `[[script]]` entry overrides the corresponding `[params]` value for that entry. The only reserved key is `text`.

### Voice cloning

```toml
model = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-bf16"

[params]
ref_audio = "reference.wav"
ref_text  = "This is what my voice sounds like."
lang_code = "auto"

[script]
text = "This is my cloned voice."
```

## Notes

- **IndexTTS**: `ref_audio` is a required argument with no default. It must be specified in `[params]` or the `[[script]]` entry.
- Models not supported by mlx-audio itself are out of scope.

## Examples

See [`examples/`](examples/) for ready-to-use TOML files.

## License

MIT
