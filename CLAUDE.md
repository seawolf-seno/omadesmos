# omadesmos

Locked-down Desmos app (Python, GTK3, WebKit2GTK 4.1) for pacos. Part of the school dev
platform initiative (see `~/.claude/CLAUDE.md`). Sibling of `omacanvas`: keep the lockdown code
(config loading, content blocker, navigation policy, downloads) in step with it.

- `omadesmos.py` is the whole app. Config: `config.json` (dev) / `/etc/omadesmos/config.json` (installed, wins).
- Never add a URL bar, env/flag config override, or dev tools.
- One WebView per calculator in a `Gtk.Stack`, so switching never reloads a page (a reload loses unsaved work).
- 3D needs the WebKit flags `AllowWebGLInWorkers` + `UseGPUProcessForWebGL`. Recheck after WebKitGTK upgrades.

## Status
- 0.1.0 works on seno's machine (2026-10-31): all six calculators, 3D renders, switching keeps
  work, off-list pages blocked, package builds.
- Not yet tested on real Framework hardware (3D depends on the GPU driver).
- In pacos 0.2.0-4 (Super+4) since 2026-11-01. VM: works for a student; 3D blank there (no GPU
  acceleration in the VM). Fizzy: PacOS board, card #45.
