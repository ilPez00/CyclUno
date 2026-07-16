# AION → JARVIS — Full AI-OS Transformation

Github: `ilPez00/aion` + `ilPez00/CyclUno`
Scope: TUI cockpit + Arduino physical deck → proactive voice-interactive AI companion

---

## DEEPSEARCH — Codebase Survey

### Two layers, one protocol

| Layer | Root | Tech | Role |
|-------|------|------|------|
| aion TUI | `/home/gio/aion/src/aion/` | Python + Textual | Cockpit, Intent routing, AI harnesses, voice, stats |
| CyclUno deck | `/home/gio/CyclUno/` | Arduino C++ (ATmega328P) | Physical input (2 joysticks, 6 buttons), OLED, LEDs |

Wire protocol: v2 framing (`0xAA 0x55 | len16 | type | payload | crc16`), shared header `cyclops_shared.h`.

### Current state

| Dimension | What exists | Gap vs Jarvis |
|-----------|-------------|---------------|
| Voice input | `VoiceInput` in `input.py` — offline faster-whisper STT, energy-VAD, intent parse | **Output only** — no TTS. Can't speak back. No personality. |
| Visuals | `UnoHud` — 16×16 text grid on 128x128 OLED. 8x8 font, no graphics | **No animation.** Text rows only. No arcs, icons, transitions. |
| AI | Multi-harness: DemoHarness, ShellHarness, CyclopsHarness(stub), AppHarness | **Reactive only.** Wait for user command. No proactive suggestions. |
| Personality | Menu items: "Notes", "Ask agent", "Home". Toast: "REC on", "REC off". | **No character.** Everything functional. No wit, no soul. |
| System integration | AppHarness (spawn + SIGSTOP/SIGCONT). TelemetryHarness (nvidia-smi/ollama polls). | **Reactive.** No proactive system monitoring. No environment awareness. |
| Memory | `MemoryStore` — flat fact list. Substring query. Persisted to JSON. | **No episodic memory.** No auto-logging of events. Can't answer "what happened today?" |
| Hardware | ATmega328P (2 KB SRAM, 32 KB flash). 56% RAM used by `UnoHud` (<400B gated). | **RAM locked.** No framebuffer graphics. No audio. No room for animations. |

### Key files

| File | Lines | Role |
|------|-------|------|
| `aion/src/aion/ui/app.py` | 350 | Textual cockpit — compose, render, key bindings, bus subscription |
| `aion/src/aion/store.py` | 231 | Intent handler + state machine ("brain") |
| `aion/src/aion/input.py` | 391 | All input: keyboard map, joystick (evdev), voice (faster-whisper), deck serial |
| `aion/src/aion/core.py` | 271 | Bus, Intent, TaskRegistry, SessionStore, Config |
| `aion/src/aion/harnesses.py` | 386 | AI backend abstraction — 6 harness types |
| `aion/src/aion/deck/link.py` | 130 | Serial transport to CyclUno (background thread) |
| `aion/src/aion/deck/protocol.py` | 126 | Wire protocol encode/decode, InputEvent |
| `aion/src/aion/memory.py` | 71 | Flat fact store, persist to JSON |
| `CyclUno/src/main.cpp` | 263 | Firmware main — loop, polling, HUD rendering, serial framing |
| `CyclUno/include/cycluno.h` | 211 | `UnoHud` — state machine, RowSink, 3 modes (HOME/NOTES/MENU) |
| `CyclUno/include/deck.h` | 82 | Input event packing, `RawAxisStream` (APP mode) |
| `CyclUno/include/joynav.h` | 61 | Joystick deadzone + auto-repeat logic |
| `CyclUno/include/cyclops_shared.h` | 155 | Shared: CRC16, `FrameDecoder`, `DisplayModel`, `UiState` |

### Risks (premortem)

| Risk | Impact | Mitigation |
|------|--------|------------|
| R1: ATmega328P RAM overflow (2 KB) | Adding graphics, animation state, audio buffers crashes firmware | MCU upgrade (ESP32-S3/RP2040) before Phase 2. Uno stays dev target. |
| R2: TTS latency > 1.5s breaks illusion | "Dead air" before response kills Jarvis feel. User loses trust. | Streaming/chunked TTS. Pre-warm model on boot. Show "thinking" indicator. Premium: ElevenLabs streaming. |
| R3: Proactive agent annoys user | Suggesting unprompted = interruptive, not helpful | Strict priority (user-safety > system-crit > suggestion). Mute/snooze. Learn user patterns. |
| R4: Personality reads fake | Witty one-liners in TUI = cringey, not Jarvis-like | Personality through *behavior* first (speed, anticipation, conciseness). Wit last. |
| R5: Scope creep kills delivery | Nothing ships if every phase is "perfect" | 3 strict phases. Each gates on previous. Phase 1 ships in days. |
| R6: aion GitHub public? | Repo returned 404. May not push upstream. | Work from local clone. Verify remote access before pushing. Fallback: local-only commits. |
| R7: Attentional user base | User has many concurrent projects. Expects fast results, may orphan. | Ship Quick Wins in 1-2 days to demonstrate value. Each phase must demonstrate value independently to maintain momentum. |
| R8: Cache poisoning risk | Old persona strings may linger in TUI text. Template substitution could leave stale markers. | Covering memory, persona, and template tests. Explicit TUI text regeneration on persona change. |

---

## FACTORY LOOP — Execution Plan

### Premortem (before any code)

- **Break CI**: Existing `make test` + `pytest tests/` must still pass. Any new code must add tests.
- **Corrupt git**: Never `git add -A`. Stage specific files only. One commit per logical unit.
- **Overwrite user work**: Verify `git status -s` before write. Stash user edits if present.
- **Stale toolchain**: `pip install -e ".[deck,voice,dev]"` in aion venv. `make test` for CyclUno (g++ host gate).
- **Rollback**: Every commit = revert point. `git reset --hard <sha>` if a step breaks.
- **Permission**: User approved batch scope above. No re-prompt per command. Smart-approve routine edits.

### Batch permission scope (asked once)

This plan covers all 3 phases. Permission covers:
- Read/write all files in `/home/gio/aion/src/aion/` and `/home/gio/CyclUno/` and `/home/gio/CyclUno/docs/`
- Run `make test`, `pytest`, `pip install`, `python3 -m aion.ui.app` (headless smoke)
- `git commit` + `git push` per cycle
- No: sudo/-H/-S installs, hardware flash without confirm

---

## PHASE 1 — Voice Loop + Personality (ship in days)

Goal: aion talks back, has a character, feels alive.

### Cycle 1.1: TTS engine

- **Write** `/home/gio/aion/src/aion/voice/output.py`
- Class `VoiceOutput`: wraps `edge-tts` (zero dep friction, fast, British voice available). Async `say(text)`. Fallback: `pyttsx3` if edge-tts missing. No-op if no audio device.
- Add optional dep `[voice-tts]` = `edge-tts` to `pyproject.toml`
- Test: `python -c "from aion.voice.output import VoiceOutput; import asyncio; asyncio.run(VoiceOutput().say('Hello, sir.'))"` → audio plays.
- Verify: `pytest tests/` still passes. No new warnings.

### Cycle 1.2: Personality module

- **Write** `/home/gio/aion/src/aion/voice/persona.py`
- `Persona` class: maps event type → response string with character.
- Patterns:
  - task DONE → "Done, sir." / "Finished. Anything else?" / "As requested."
  - task FAILED → "Hit a snag. Let me try another approach."
  - startup → "Good [morning/afternoon/evening]. Aion online. All systems nominal."
  - idle 5m → "Standing by." (once, not repeated)
- Attributes: `verbosity` (terse/normal/chatty), `formality` (formal/casual), `name` ("aion").
- Persist persona config to `~/.aion/persona.json`.
- Config in `config/layout.json` -> `persona: { name, verbosity, formality }`.
- Test: unit tests for event→response mapping. Assert not empty, <200 chars, no unprintable chars.

### Cycle 1.3: Wire TTS into bus

- **Edit** `/home/gio/aion/src/aion/store.py` — subscribe to task state in `_on_task_event`. On DONE/FAILED/CANCELLED, emit voice event.
- **Edit** `/home/gio/aion/src/aion/ui/app.py` — on boot, init `VoiceOutput` and subscribe to voice events. Create `_on_voice(msg)` that calls `voice.say(msg.text)`.
- Rate limit: not per progress tick. Only on state transitions + significant events.
- Test: simulate task completion → verify `VoiceOutput.say()` called with persona response string.

### Cycle 1.4: Personality in TUI text

- **Edit** `/home/gio/aion/src/aion/ui/app.py` — replace bottom bar help string with character intro on boot. Replace "running: 2" with "two tasks in progress" style.
- **Edit** `/home/gio/aion/src/aion/store.py` — use personality module for status lines in history.
- Test: assert bottom bar != raw help string after 1s. Assert task count uses natural language.

### Cycle 1.5: Quick-win theme + startup

- **Edit** `config/layout.json` — add "Jarvis" theme preset (cyan `#00d4ff` accent, orange `#ff8c00` warn, deep blue `#0a1628` bg).
- **Edit** `/home/gio/aion/src/aion/ui/app.py` — on `on_mount`, print "Aion online. All systems nominal." with typing effect on bottom bar. Play startup chime via `paplay` or `aplay` (optional WAV in `~/.aion/sounds/`).
- Test: boot, see "Aion online..." in bottom bar. No crash if no audio device.

**Phase 1 gate**: user hears "Good morning. Aion online." on boot. Tasks complete with "Done, sir." spoken. TUI text matches character. All existing tests pass.

---

## PHASE 2 — Visual Richness + Proactive Behavior

Goal: deck OLED animates, TUI shows live charts, aion suggests before asked.

### Cycle 2.1: Deck MCU upgrade (ESP32-S3)

- **Write** new build target in `CyclUno/platformio.ini`: `[env:esp32s3]` using `platform = espressif32`, `board = esp32-s3-devkitc-1`.
- **Add** `CyclUno/include/cycluno_gfx.h` — graphics mode HUD alongside text `UnoHud`.
- Upgrade opens: 512 KB SRAM (vs 2 KB), 240 MHz dual-core, I2S for audio, WiFi/BLE.
- Keep backward compat: `make build` still compiles Uno target.
- Verify: `pio run -e esp32s3` compiles without error (no flash needed for gate).

### Cycle 2.2: Animated OLED UI

- **Write** `CyclUno/include/cycluno_gfx.h` — class `AnimatedHud`:
  - Progress arcs (circle that fills clockwise) for task progress
  - Smooth scroll between notes (vertical slide, not jump-cut)
  - Status icons: mic pulse when voice active, glowing REC dot
  - Fade transitions between HOME/NOTES/MENU modes
  - Boot animation: "AION" draws in, glow pulse, fade to HUD
  - U8g2 framebuffer mode (not tile-based text)
- **Edit** `CyclUno/src/main.cpp` — switch renderer based on build target (`#ifdef ESP32` block).
- Verify: host-gate test feeds frame data, asserts pixel buffer changes between renders.

### Cycle 2.3: System tones on deck

- **Add** piezo buzzer pin (D9) to BOM for ESP32 build.
- **Edit** `CyclUno/src/main.cpp` — play tones:
  - Power-on: rising two-note chime (440Hz→880Hz, 100ms each)
  - Task complete: single 660Hz 80ms
  - Error: low 220Hz 200ms
  - Mode switch: short click 1kHz 10ms
- Config: `SoundProfile` enum (normal/silent/loud). Set in firmware build flags.
- Verify: tone patterns produce expected frequency + timing (oscilloscope or manual listen).

### Cycle 2.4: Rich TUI sparklines + themes

- **Edit** `/home/gio/aion/src/aion/ui/app.py`:
  - Right rail: live sparkline for task throughput (last 60s, unicode braille characters)
  - VRAM usage bar: green→yellow→red gradient
  - Task progress: braille fill for sub-character resolution
  - Header clock: show seconds ticking
  - Theme presets: "Jarvis" (cyan/orange), "Night" (muted blues), "Hologram" (green/cyan)
- Test: sparkline updates without widget remount (performance regression guard).

### Cycle 2.5: Proactive engine

- **Write** `/home/gio/aion/src/aion/proactive.py` — class `ProactiveEngine`:
  - Timer loop (every 30s). Watch conditions:
    - CPU > 90% for 30s → "System under load. Pause background?"
    - 12+ facts without query → "12 facts accumulated. Summarize?"
    - 5min no input → "Standing by." (once)
    - Task chain: finished + queued → "Next task ready. Start?"
  - Strict debounce: max 1 proactive event per 60s. User input resets idle.
  - Quiet mode: suppress all proactive. Config in `config/layout.json`.
- **Edit** `/home/gio/aion/src/aion/store.py` — connect proactive engine to bus.
- **Edit** `/home/gio/aion/src/aion/ui/app.py` — display proactive suggestions as toasts.
- Test: mock conditions, assert correct suggestion fires. Quiet mode suppresses all.

**Phase 2 gate**: OLED shows animated arcs, smooth scroll, boot logo. TUI has live sparkline + VRAM bar. Proactive engine offers context suggestions without being annoying. All Phase 1 + Phase 2 tests pass.

---

## PHASE 3 — Integration + Memory + Polish

Goal: system awareness, rich memory, wake word, settings hub, cinematic startup.

### Cycle 3.1: System monitoring harness

- **Edit** `/home/gio/aion/src/aion/harnesses.py` — upgrade `TelemetryHarness` to `SystemHarness`:
  - CPU per-core usage, load average
  - RAM used/total/available
  - Disk I/O, space usage
  - Network throughput (tx/rx per interface)
  - Running processes (count + top 3 by CPU)
  - Battery level (if laptop)
- Output: stats published on bus every 5s. Right rail shows live SYNC panel.
- Test: mock `/proc` fixtures, assert correct stat parsing. Graceful degrade when `/proc` inaccessible.

### Cycle 3.2: Enhanced memory (episodic + semantic)

- **Edit** `/home/gio/aion/src/aion/memory.py`:
  - Episodic: auto-log significant events to `~/.aion/episodes/YYYY-MM-DD.jsonl`.
    - Schema: `{ts, type:"task_done"|"voice_cmd"|"note_added", text, detail:{}}`
  - Semantic: facts (`note`) keep existing behavior. Add tags support (`#urgent`).
  - Recall: `mem query` searches both episodic and semantic stores. Results with timestamp + source tag.
  - Auto-archive: facts > 90d move to `~/.aion/memory.archive.json`.
- Test: auto-log fires on task done. Search returns both episodic + semantic results. Archive triggers correctly.

### Cycle 3.3: Voice personality polish

- **Edit** `/home/gio/aion/src/aion/voice/output.py`:
  - SSML support for emotion/emphasis in TTS (`<emphasis level="strong">`, `<prosody rate="slow">`).
  - Multiple piper-tts voice variants: one neutral, one alert (higher pitch/rate).
- **Edit** `/home/gio/aion/src/aion/voice/input.py` (`VoiceInput`):
  - Add wake word "Aion..." via Porcupine or openWakeWord.
  - Wake word activates listen mode without pressing `v`.
  - Interrupt: if aion speaks and user speaks, stop TTS + start listening.
- **Edit** deck OLED: show mic icon with animation when voice active.
- Test: wake word triggers listen. Interrupt stops TTS mid-word.

### Cycle 3.4: Settings hub

- **Write** `/home/gio/aion/src/aion/ui/settings_screen.py` — new workspace "Settings":
  - Voice: TTS speed (0.5x-2x), voice gender (male/female), volume, wake word on/off, quiet hours (start/end)
  - Personality: verbosity (terse/normal/chatty), formality (formal/casual), name
  - Proactive: toggle per category (system/memory/idle)
  - Theme: dropdown of presets, preview applies in real-time
  - Deck: OLED brightness (0-100), animation speed (slow/normal/fast), sound profile (normal/silent/loud)
- **Edit** `/home/gio/aion/config/layout.json` — add "settings" workspace.
- **Edit** `/home/gio/aion/src/aion/store.py` — persist settings to `~/.aion/settings.json`.
- Test: load/save round-trip for every setting. Theme switch doesn't crash.

### Cycle 3.5: Cinematic startup

- **Edit** `/home/gio/aion/src/aion/ui/app.py`:
  - Boot sequence: "AI engines... online." → "Voice synthesis... calibrated." → "Memory stores... loaded." → "Control deck... linked." Each line typing effect, 300ms pause.
  - Then: "Good morning, sir. All systems nominal." (uses persona greeting).
- **Edit** `CyclUno/src/main.cpp` (or `cycluno_gfx.h`):
  - Animated "AION" logo on OLED boot: draw letter-by-letter, glow pulse, blink 2x, transition to HUD.
- **Edit** `VoiceOutput` — play startup chime at boot.
- Test: boot sequence renders without blocking UI. Deck animation finishes within 3s.

**Phase 3 gate**: Full Jarvis feel — wake word, system-aware, rich memory recall, cinematic startup, fully customizable settings. All 3 phases' tests pass.

---

## VERIFICATION GATES

### Every cycle

```bash
# aion
cd /home/gio/aion && .venv/bin/python -m pytest tests/ -v

# CyclUno host gate
cd /home/gio/CyclUno && make test

# CyclUno compile gate (both targets if ESP32 added)
cd /home/gio/CyclUno && make build && pio run -e esp32s3
```

### Phase gates

| Phase | Gate | Who verifies |
|-------|------|-------------|
| 1 | User hears TTS. TUI shows character text. All tests pass. | dev + manual listen |
| 2 | OLED animates. TUI shows sparklines. Proactive suggestion fires. | dev + visual check |
| 3 | Wake word works. Memory recall returns episodes. Startup cinematic plays. | dev + manual |

### Manual checks per phase

- Phase 1: mouth-to-ear < 2s. Personality reads natural (not robotic/annoying).
- Phase 2: OLED animation > 15 fps perceived. Proactive: 1h usage, log all suggestions, review.
- Phase 3: wake word detection rate > 80% in quiet room. Memory recall relevant to query > 70%.

---

## COMMIT DISCIPLINE

Per factory-loop:

1. `git diff --cached --name-only` before commit — no stray files
2. One commit per logical unit (not per day)
3. Commit message: conventional commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`)
4. `git push` only on green (all tests pass)
5. Branch per phase: `jarvis/p1`, `jarvis/p2`, `jarvis/p3`
6. No `git add -A`. Explicit paths only.

Rollback: `git reset --hard <pre-commit-sha>` if a step breaks CI or corrupts behavior.
