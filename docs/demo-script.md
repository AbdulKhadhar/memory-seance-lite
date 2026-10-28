# Demo recording script (60 to 90 seconds)

Use only the fictional sample data: `python scripts/load_sample.py`.

## Before you record (checklist)

- [ ] Ollama is running (`ollama list` works).
- [ ] The small model is pulled and selected (gemma3:1b, or qwen3:0.6b on very low RAM). The header badge says "Ollama ready".
- [ ] Browser window is clean: no extra tabs, bookmarks bar hidden, notifications off.
- [ ] Sample memories are loaded. No personal or private data is on screen.
- [ ] A terminal is open beside the browser showing the `python -m app.main` logs (to show inference is local).
- [ ] Do one warm-up question first so the model is already loaded in memory.

## Recording settings for low-end hardware

720p, 24 to 30 fps, capture a single window (not the whole desktop), microphone off (use text overlays), close other apps.

- **Windows Game Bar:** Win+G, click Capture, Record (or Win+Alt+R). In Settings, Capturing, set video frame rate to 30 fps and standard quality. Files land in Videos/Captures. Game Bar records one app window, so focus the browser first.
- **GNOME built-in recorder:** press Print Screen, choose the Screen Recording tab, then Window, and start. Stop from the red indicator in the top bar. Files land in Videos/Screencasts.
- **OBS Studio:** Settings, Video: base and output resolution 1280x720, FPS 30. Output: Recording, x264 (or a hardware encoder), CRF 28. Add a "Window Capture" source for the browser, and optionally a second one for the terminal.

## Script

| Time | On screen | Overlay caption |
|---|---|---|
| 0:00 to 0:08 | Terminal showing the app logs, then the browser at the app header. | "Memory Séance Lite runs entirely on this computer." |
| 0:08 to 0:20 | Memories tab. Scroll through the sample memories for Abuela Marisol. | "Memories are saved in a local SQLite file." |
| 0:20 to 0:32 | Add a memory: title "Her radio again", subject "Abuela Marisol", text "She sang along to the radio when it rained." Click Save memory. | "Add a small, true detail." |
| 0:32 to 0:50 | Ofrenda tab. Choose Abuela Marisol, click Light the candle. Glance at the terminal while it runs, then show the result. | "A small local model (gemma3:1b) writes only from your memories." |
| 0:50 to 1:10 | Séance tab. Ask "What did she grow in the garden?". Expand "Memories used". | "Every answer shows the memories it used." |
| 1:10 to 1:20 | Ask "What was her favorite football team?". Show the refusal. | "No memory, no answer. Nothing is invented." |
| 1:20 to 1:30 | Settings tab: point at the model dropdown (qwen3:0.6b option) and the Delete all memories button. | "Swap models. Delete everything anytime." |
| 1:30 | Closing card or the Memories tab. | **"Your memories stay on your machine."** |

State in the caption or video description that the séance is a creative memorial conversation, not communication with a deceased person.
