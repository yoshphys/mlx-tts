# mlx-tts

TOML-driven TTS wrapper for [mlx-audio](https://github.com/Blaizzy/mlx-audio) on Apple Silicon.

## Requirements

- Python 3.11+ (or 3.8+ with `pip install tomli`)
- [mlx-audio](https://github.com/Blaizzy/mlx-audio)
- soundfile

```sh
pip install mlx-audio soundfile
```

## Usage

```sh
python mlx_tts.py config.toml
python mlx_tts.py config.toml --dry-run   # validate without running
```

Output paths are derived automatically from the TOML filename:

| Script section | Output |
|----------------|--------|
| `[script]` | `./<stem>.<format>` |
| `[[script]]` | `./<stem>/<stem>_000.<format>`, `<stem>_001.<format>`, … |

## TOML format

### Minimal

```toml
model = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

[script]
text = "Hello, world."
```

### Single text

```toml
format = "wav"   # wav | flac | mp3  (default: wav)
model  = "mlx-community/Qwen3-TTS-12Hz-0.6B-Base-4bit"

[params]
# Keys are passed directly to model.generate() — any argument the model accepts is valid.
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

`[[script]]` defines a list of entries. Each entry can override any `[params]` key. Reserved keys per entry: `text`, `enabled`.

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

### Disabling entries

Set `enabled = false` to skip generation of an entry while keeping its index. This ensures the output filenames of subsequent entries are not affected.

```toml
[[script]]
text  = "This is segments_000."
voice = "Ryan"

[[script]]
enabled = false
text    = "This entry is skipped. Its slot (001) is still reserved."
voice   = "Vivian"

[[script]]
text  = "This is segments_002, not 001."
voice = "Ryan"
```

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

## Parameters

All keys in `[params]` are passed directly to `model.generate()`. Supported parameters vary by model.

### Descriptions

| param | type | description |
|-------|------|-------------|
| `voice` | string | Preset speaker name. Available names differ per model (e.g. `"Ryan"`, `"Vivian"` for Qwen3-TTS; `"af_heart"` for Kokoro). |
| `speaker` | int | Speaker index for models that identify speakers numerically. |
| `lang_code` | string | Language code. `"auto"` works for Qwen3-TTS. Kokoro uses single-letter codes (`"a"` = American English, `"b"` = British English, `"j"` = Japanese, etc.). |
| `instruct` | string | Emotion/style instruction (Qwen3-TTS CustomVoice) or free-text voice description (Qwen3-TTS VoiceDesign). |
| `speed` | float | Speech speed multiplier. `1.0` = normal. |
| `temperature` | float | Sampling temperature. Lower = more stable; higher = more varied. |
| `top_k` | int | Restricts sampling to the top-k most likely tokens at each step. |
| `top_p` | float | Nucleus sampling: tokens are drawn from the smallest set whose cumulative probability exceeds this value. |
| `repetition_penalty` | float | Penalty applied to repeated tokens. `1.0` disables it. |
| `max_tokens` | int | Maximum number of tokens to generate. |
| `ref_audio` | string | Path to a reference audio file for voice cloning. |
| `ref_text` | string | Transcript of `ref_audio`. Providing this improves cloning quality. |
| `split_pattern` | string | Regex pattern used to split long text into chunks (e.g. `"\n"`, `r"(?<=[.!?])\s+"`). |
| `stream` | bool | Enable streaming generation; audio chunks are yielded incrementally. |
| `streaming_interval` | float | Duration in seconds of each streamed audio chunk. |

### Support by model

`✓*` = required (no default). `✓†` = supported under a different key name.

| param | bark | pocket_tts | echo_tts | qwen3_tts | outetts | kokoro | spark | voxcpm | sesame | chatterbox | indextts | soprano | fish_qwen3_omni | kitten_tts | dia | llama |
|-------|:----:|:----------:|:--------:|:---------:|:-------:|:------:|:-----:|:------:|:------:|:----------:|:--------:|:-------:|:---------------:|:----------:|:---:|:-----:|
| `voice` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | | | ✓ | ✓ | | | | ✓ | ✓ | |
| `speaker` | | | | | | | | | ✓ | ✓ | | | | | | |
| `lang_code` | | | | ✓ | | ✓ | | | | | | | | ✓ | | |
| `instruct` | | | | ✓ | | | | | | | | | | | | |
| `speed` | | | | ✓ | | ✓ | ✓ | | | | | | | ✓ | | |
| `temperature` | | ✓ | | ✓ | ✓ | | ✓ | | | | | ✓ | ✓ | | ✓ | |
| `top_k` | | | | ✓ | ✓ | | ✓ | | | | | ✓ | ✓ | | | |
| `top_p` | | | | ✓ | ✓ | | ✓ | | | | | ✓ | ✓ | | ✓ | |
| `repetition_penalty` | | | | ✓ | ✓ | | | | | | | ✓ | | | | |
| `max_tokens` | | | | ✓ | ✓ | | ✓ | ✓ | | | ✓ | ✓† | ✓† | | | |
| `ref_audio` | | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | ✓ | ✓ | ✓* | ✓† | | | ✓ | ✓ |
| `ref_text` | | | | ✓ | | | ✓ | ✓ | ✓ | ✓ | | | | | ✓ | ✓ |
| `split_pattern` | | | | ✓ | ✓ | ✓ | ✓ | | ✓ | ✓ | | ✓ | | ✓ | ✓ | |
| `stream` | | ✓ | ✓ | ✓ | ✓ | | | | ✓ | ✓ | | | | | | |
| `streaming_interval` | | ✓ | | ✓ | ✓ | | | | ✓ | ✓ | | | | | | |

**Model-specific notes:**
- `indextts`: `ref_audio` is required with no default
- `soprano`: uses `reference_audio` instead of `ref_audio`, and `max_new_tokens` instead of `max_tokens`
- `fish_qwen3_omni`: uses `max_new_tokens` instead of `max_tokens`
- `spark`: has additional params `gender` (string) and `pitch` (float)
- `voxcpm`: has additional params `inference_timesteps` (int) and `cfg_value` (float)

## Examples

See [`examples/`](examples/) for ready-to-use TOML files.

## License

MIT
