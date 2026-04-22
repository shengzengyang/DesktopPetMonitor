# CLAUDE.md — Architecture & Dev Guide for AI Agents

This file is specifically written for Claude / Claude Code / any AI coding
assistant that opens this project. Read it **before** making changes.

The project is about ~2500 lines of Python wrapping a Live2D desktop pet.
It looks small, but there are several Qt / Live2D / SSE quirks you must
respect — each was discovered the hard way. Most landmines are documented
below with the exact symptom they produce.

---

## TL;DR

- **Entry point**: `main.py` → `App` class → `PetWidget` (the QOpenGLWidget
  showing doro) + `InfoPanel` (floating stats window).
- **Config**: singleton in `config.py`, persisted to
  `%APPDATA%/DesktopPetMonitor/config.json`.
- **LLM**: `llm_service.py` runs a `QThread` worker, routes by model name
  (`gpt-5*` / `o1*` → `/v1/responses`, else `/v1/chat/completions`). Streams
  SSE, forces UTF-8 decoding.
- **Live2D**: `live2d.v3` C bindings via `live2d-py`. Models go under
  `assets/<kind>/<name>/`.
- **i18n**: dict-based, in `i18n.py`. Call `t('some.key')` for strings.
- **Logging**: `logger.py` exposes `log` (Python `logging`). Writes
  `doro.log` + stderr.

---

## File map

```
main.py              App shell, QApplication, tray menu, signal wiring
pet_widget.py        PetWidget (QOpenGLWidget) — renders doro, mouse events,
                     context menu, wander loop, drag/struggle, motion loop
                     retrigger
info_panel.py        Floating system monitor panel + pomodoro + IP alert
chat_input.py        The tiny "talk to doro" popup (Qt.Popup, not Qt.Tool!)
speech_bubble.py     Transparent bubble above doro
settings_dialog.py   5 tabs of settings
llm_service.py       QThread LLM worker with /v1/chat/completions
                     and /v1/responses paths
pets.py              PETS dict: name / model path / expressions / motions /
                     chats per character
config.py            Defaults + JSON persistence singleton
monitors.py          psutil + pynvml wrapper
ip_fetcher.py        Background IP fetcher (direct + proxy)
reminder.py          SitReminder + Pomodoro QObjects
i18n.py              Dict-based translations
logger.py            Rotating file logger
assets/              Live2D models (Haru sample + Dororong)
tools/               Dev scripts:
                       generate_motions.py  — regenerate motion3.json files
                       param_explorer.py    — screenshot each param
                       snap_expressions.py  — screenshot each expression
                       snap_motions.py      — mid-frame of each motion
                       diagnose_motions.py  — smoke-test motion loading
                       test_motions.py      — ad-hoc motion tester
                       test_one_motion.py   — ditto for one file
```

---

## Known landmines (read before touching!)

### 1. `MotionPriority.FORCE` is an **int**, not an enum

`live2d.v3.MotionPriority` is a plain class with int constants. If you see
`MotionPriority.FORCE.value` anywhere, that's a bug — `.value` throws
`AttributeError`. Use `MotionPriority.FORCE` directly.

### 2. `Qt.Tool` windows on Windows hide each other

Two `Qt.Tool` windows in the same app can trigger "orphan tool auto-hide"
on Windows — hiding one makes the other disappear.

- `PetWidget` is `Qt.Tool` (correct).
- `ChatInput` and `SpeechBubble` used to be `Qt.Tool` too → caused doro to
  disappear after a chat. Now `ChatInput` is `Qt.Popup`, `SpeechBubble`
  is `Qt.Tool + Qt.WindowTransparentForInput` but **parented to the pet**
  so Qt tracks ownership.
- `PetWidget.say()` has a belt-and-suspenders `if not self.isVisible():
  self.show(); self.raise_()` to recover from any future regression.

### 3. `live2d-py` ignores `"Loop": true` in motion3.json

You have to detect `IsMotionFinished()` and re-trigger the motion manually.
The logic lives in `PetWidget._anim_tick()`. Two rules:

- If `self._loop_motion` is set → restart it.
- Otherwise if state is `idle` → fall back to `Idle` group.

Any new looping motion group must be added to the top-of-file
`LOOPING_GROUPS` set. Currently: `{'Idle', 'Dance', 'Run'}`.

### 4. `requests` defaults SSE responses to Latin-1

HTTP spec fallback when `Content-Type` has no charset. The LLM worker
explicitly sets `r.encoding = 'utf-8'` before `iter_lines()`. If you see
garbled Chinese in replies, you forgot this.

### 5. Cubism JSON parser is picky

- Near-zero floats like `3.67e-16` (scientific notation) crash the parser.
  `tools/generate_motions.py` clamps |v| < 1e-4 to 0.0 to avoid it.
- Compact single-line JSON objects (`{"File":"x",...}`) also fail on some
  versions. Always write motion3.json indented.

### 6. Doro has NO arm / leg parameters

Check `assets/dororong/Doro/Doro.cdi3.json` — 38 params, none named
`ParamArmL/R` or `ParamLegL/R`. The "running" effect comes from oscillating
`ParamStep ±10` (body gait lurch) + `AnimLine` (speed lines) + bounce
inputs. You cannot make doro literally wave or lie down — the source
`.cmo3` project file isn't shipped, only the compiled `.moc3`. See
`NIGHT_PROGRESS.md` (if present) for the parameter dictionary built from
screenshot exploration.

### 7. Silent `except: pass` is banned

All calls into `live2d-py` or `requests` that fail must be logged via
`log.exception(...)` or `log.warning(...)`. A silent swallow in the
motion path once cost multiple hours of debugging (see saved feedback
memory about `MotionPriority.FORCE.value`).

---

## How to add a new pet model

1. Drop the Live2D model files into `assets/<kind>/<name>/`:
   ```
   assets/mypet/MyPet/
     MyPet.moc3
     MyPet.model3.json
     MyPet.physics3.json
     MyPet.cdi3.json
     MyPet.2048/texture_00.png
     Motions/*.motion3.json
     Expressions/*.exp3.json
   ```

2. Open `Doro.cdi3.json` and list what parameters actually exist (you may
   need to run `tools/param_explorer.py` pointed at the new model — edit
   `MODEL = ROOT / 'assets' / 'mypet' / 'MyPet' / 'MyPet.model3.json'`).

3. Add an entry to `pets.PETS`:
   ```python
   'mypet': {
       'name': 'MyPet (display name)',
       'model_rel': 'assets/mypet/MyPet/MyPet.model3.json',
       'size': (220, 340),                 # base pixel size at scale=1.0
       'hit_head_motion': ('TapHead', 0),
       'hit_body_motion': ('TapBody', 0),
       'idle_group': 'Idle',
       'expressions': { 'happy': 'F01', 'alert': 'F07', ... },
       'named_expressions': [...],          # optional: menu entries
       'tap_motions': ('TapBody', 4),
       'named_motions': [
           ('nod', '✅ Nod', 'Nod', 0),
           ('dance', '💃 Dance', 'Dance', 0),
           ...
       ],
       'chats': { 'idle': [...], 'drag': [...], ... },
   },
   ```

4. If your model has looping motions, **add the group name to
   `LOOPING_GROUPS` in `pet_widget.py`** or they'll stop after one cycle.

5. Launch and test: right-click doro → 🧸 Switch Model → choose yours.

---

## How to add / modify a motion

Motions are programmatically generated in `tools/generate_motions.py`.

```python
MOTIONS['my_new_motion'] = motion([
    smooth_curve('ParamAngleX', [(0, 0), (0.5, 20), (1.0, 0)]),
    sine_curve('ParamBreath', 1.0, amp=0.5, cycles=2, offset=0.5),
    ...
], duration=1.0, loop=False)
```

Then:
1. Run `python tools/generate_motions.py` — writes new `.motion3.json`
   under `assets/dororong/Doro/Motions/`.
2. Register the motion group in `Doro.model3.json`:
   ```json
   "MyNewGroup": [
       { "File": "Motions/my_new_motion.motion3.json",
         "FadeInTime": 0.2, "FadeOutTime": 0.3 }
   ]
   ```
3. Add a menu entry in `pets.PETS['dororong']['named_motions']`.
4. If `loop=True`, add the group to `LOOPING_GROUPS`.

The three key curve helpers:

| helper | when to use |
|---|---|
| `linear_curve(id, [(t, v), ...])` | straight linear segments between keyframes |
| `smooth_curve(id, [(t, v), ...])` | smoothstep-eased interpolation, softer feel |
| `sine_curve(id, duration, amp, cycles, ...)` | continuous oscillation (breath, sway) |
| `stepped_osc(id, duration, low, high, period)` | rapid toggle (used for `ParamStep` in Run) |

Always clamp near-zero floats to 0.0 (already done by `_clean()`).

---

## How to add UI strings

All strings user-facing go through `i18n.t('key')`. Add the key to both
`zh` and `en` catalogs in `i18n.py`. The fallback chain is
`current_lang → zh → key itself` so partial translations still render.

```python
# i18n.py
'zh': {
    'my_section.my_string': '你好',
},
'en': {
    'my_section.my_string': 'Hello',
},
```

```python
# elsewhere
from i18n import t
widget.setText(t('my_section.my_string'))
```

For placeholders: `t('key', name=value)` formats with `.format(**kwargs)`.

**Gotcha**: labels read `t()` at widget construction time. Language
changes after startup don't retro-update already-built widgets — a
restart-to-apply hint is shown in the settings dialog.

---

## LLM worker details

`llm_service.py::LLMWorker.run()` dispatches based on model name:

```
_is_responses_api_model(model) ?
    → _run_responses(model)        # /v1/responses, Responses API
    → _run_chat_completions(model) # /v1/chat/completions, standard OpenAI
```

Both paths:
- Force `stream=True` at the request level
- `r.encoding = 'utf-8'` before streaming
- Parse SSE line by line via `r.iter_lines(decode_unicode=True)`
- Emit `self.failed.emit(...)` or `self.replied.emit(text)` on done

To add a new provider / API format:
1. Extend `_is_responses_api_model()` or add a new predicate
2. Add a new `_run_xxx(model)` method following the same SSE pattern
3. Route it in `run()`

---

## Logging conventions

```python
from logger import log
log.debug('...')    # verbose, not shown on stderr
log.info('...')     # normal events (app start, motion play, LLM call)
log.warning('...')  # recoverable problems (HTTP 429, missing config)
log.error('...')    # serious errors (JSON parse fail, API 500)
log.exception('...')# use inside `except:` — auto-adds traceback
```

**Rule**: any `except:` block that calls into `live2d-py` or `requests`
must log. If you see `except: pass` in a PR, reject it.

Log path is `<project_root>/doro.log` (rotated 5 MB × 3). Tail it during
testing; include the relevant lines in every bug report.

---

## Environment assumptions

- Windows 10/11 — most of the Qt quirks (translucent OpenGL widget, Tool
  window hiding, WS_EX_LAYERED rebuild) are Windows-specific. The code may
  run on macOS / Linux but was never tested there.
- **Python 3.10 64-bit** — `live2d-py` only ships wheels for 3.10, not 3.11+.
  Using 3.11/3.12/3.13 will fail at `pip install`. From source, create the
  venv explicitly with `py -3.10 -m venv venv`.
- OpenGL 3.0+ — Cubism Core requires it for the shader pipeline.
- **No VC++ Redistributable install needed by end users** — the packaged
  exe bundles the MSVC 2015-2022 runtime DLLs itself (see next section).

---

## Building the distributable exe

PyInstaller produces a single-file exe under `dist/DesktopPet.exe`
(~42 MB) that includes Python, all deps, Live2D assets, and the MSVC
runtime — end users don't need Python or VC++ Redistributable installed.

Run either:

```bash
./build.bat                         # full pipeline (venv check + install + build)
venv/Scripts/python -m PyInstaller --noconfirm --clean DesktopPet.spec
```

### What's inside the bundle

`DesktopPet.spec` is the authoritative build recipe:

- `datas=[('assets', 'assets')]` — bundles the whole `assets/` tree so
  Live2D models are available at runtime.
- `_msvc_binaries` — scans `C:\Windows\System32` and bundles these DLLs
  at the bundle root (critical that they're at root, not in a subdir,
  because `live2d.pyd` can't find them if they're buried under
  `PyQt5/Qt5/bin/` where PyInstaller's default Qt hook places its own
  copies):
    - `msvcp140.dll`, `msvcp140_1.dll`, `msvcp140_2.dll`
    - `vcruntime140.dll`, `vcruntime140_1.dll`
    - `concrt140.dll` — Microsoft Concurrency Runtime (Live2D threads)
    - `vccorlib140.dll`

### Frozen-mode path quirks

When running as a `--onefile` exe, PyInstaller extracts everything to a
temp dir exposed as `sys._MEIPASS`. Two modules have to handle this:

- `pets.py` — uses `sys._MEIPASS` when frozen so asset paths resolve.
- `logger.py` — writes `doro.log` to `%APPDATA%/DesktopPetMonitor/`
  (not next to the exe), otherwise PyInstaller wipes the log on exit.

If you add new code that reads files from the project directory, use
the same `getattr(sys, 'frozen', False)` check.

### No user data in the bundle

The exe is verified clean via `strings dist/DesktopPet.exe | grep ...`
for API keys, QQ emails, proxy URLs, configured IPs, and build-machine
paths. User config + log always live in `%APPDATA%/DesktopPetMonitor/`
— never embedded in the bundle. After every rebuild, run the scan
before publishing the release:

```bash
strings dist/DesktopPet.exe | grep -iE "sk-|bearer|@gmail|qq\\.com|googogogo|lyxnb|11373|\\bC:\\\\Users\\\\[^\\\\]+"
```

If that's empty, the bundle is safe to upload.

### Publishing to GitHub Releases

```bash
gh release upload v0.1.0 dist/DesktopPet.exe --clobber
```

The `--clobber` flag overwrites the previous asset with the same name,
so existing download links keep working.

---

## Testing

There's no formal test suite. Dev loop looks like:
```bash
python main.py                        # run the pet
python tools/diagnose_motions.py      # smoke test motion loading
python tools/generate_motions.py      # regenerate motion3.json files
python tools/param_explorer.py        # screenshot all parameters
```

After any change to `pet_widget.py` / `llm_service.py` / motion files:
1. Kill running pet
2. Relaunch
3. Check `doro.log` for startup errors (grep for `ERROR` / `Traceback`)
4. Right-click → try the affected feature
5. If it's visual, use `tools/snap_motions.py` and read the PNG.

---

## Quick sanity commands

```bash
# Is doro running?
powershell "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }"

# Tail log during testing
Get-Content doro.log -Wait -Tail 30

# Regenerate everything motion-related
python tools/generate_motions.py
```

Good luck. The pet appreciates it.
