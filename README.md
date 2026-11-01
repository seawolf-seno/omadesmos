# Omadesmos

The Desmos calculators for Omarchy, in one window with no address bar. It can't be used as
a general browser.

- **Every calculator, in full:** Graphing, 3D, Geometry, Scientific, Basic (four-function)
  and Matrix. It runs the real desmos.com, so new Desmos features show up on their own.
- **Switching keeps your work.** Each calculator stays loaded once opened. Use the header
  buttons or Ctrl+1 to Ctrl+6. The app reopens on the last calculator you used.
- Desmos accounts (email or Google sign-in), saving graphs and image export (to `~/Downloads`) work.
- Pages outside Desmos are blocked with a short notice. Camera, mic and location are off.

## Run

```sh
./omadesmos.py                 # dev: uses ./config.json
make pkg && sudo pacman -U omadesmos-*.pkg.tar.zst   # install as "Desmos" in the launcher
```

Needs `python-gobject`, `gtk3` and `webkit2gtk-4.1` (already on Omarchy).

## Configure

The installed config is `/etc/omadesmos/config.json` (root-owned). When it exists it always
wins, and students can't override it.

| Key | Meaning |
|---|---|
| `desmos_url` | Desmos site. Its host and subdomains are always allowed. |
| `allowed_hosts` | Extra hosts that may open as a page. Default: `accounts.google.com`, for "Sign in with Google". |

## How it works

- Same lockdown as OmaCanvas: a WebKit content blocker (loaded before anything opens, so it
  fails closed) plus a navigation policy for pages and new windows.
- The 3D calculator draws with WebGL inside a worker. WebKitGTK only allows that with two
  feature flags on (`AllowWebGLInWorkers`, `UseGPUProcessForWebGL`); without them Desmos
  says the browser isn't supported.
