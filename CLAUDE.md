# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Dota 2 timer PWA (UI and README are in Russian): countdowns for bounty runes, water/power runes, wisdom shrines, Tormentor, plus the day/night cycle. Vanilla HTML/CSS/JS, no build step, no dependencies, no package manager, no tests, no linter.

- **Run:** open `index.html` in a browser, or serve the folder (e.g. `python -m http.server`) — the service worker only registers on `https:` (see the `location.protocol` check at the end of the script), so offline/install behaviour can't be tested over plain `http://localhost` without changing that check.
- **After changing any cached file (`index.html`, `manifest.json`, icons), bump `CACHE` in `sw.js`** (`dota-timer-vN`), otherwise installed phones keep serving the old version. Navigations are network-first, but the bump is what evicts the old cache.

## Architecture

Everything lives in one IIFE inside `index.html` (CSS in `<style>`, markup, then `<script>`). `sw.js` is the offline cache; `manifest.json` is the install metadata.

**Game clock is anchor-based, not a counter.** `state.anchorGame` + `state.anchorEpoch` record "game time X at wall-clock Y"; `gameTime()` derives the current time from `Date.now()` while `state.ticking`. Pause, ±1/±10s sync, and "join mid-game" all work by calling `setGameTime()` to re-anchor. `state` (incl. settings) is persisted to `localStorage` under `dotaRuneTimer.v1` via `save()`; `load()` discards a saved game older than 3h.

**Events are data-driven via the `EVENTS` array** at the top of the script (game-time seconds). Each entry has `first` + `interval`, or `manual: true` + `respawn` for Tormentor (next spawn = kill time + respawn, marked with a button, hence `state.tormentKilled`). Optional `variant(s)` swaps name/icon/colour per spawn time (the river slot is "water" at 2:00/4:00, then "power rune"). `look(ev, s)` resolves the effective name/say/icon/sound/colour; `nextSpawn`/`prevSpawn` compute schedule and ring progress. Adding an event also needs an entry in `ICONS`, `SOUNDS`, `SOUND_LEN`, and a `--<color>` CSS variable; the settings toggles and cards are generated from `EVENTS`.

**Render loop:** `setInterval(render, 200)` calls `checkAlerts(t)` then updates the DOM. `checkAlerts` fires warn/spawn alerts by comparing `lastT` → `t` across each tick; it ignores gaps `<=0` or `>2s`, so anything that jumps the clock (sync buttons, pause, resume, tab visibility) must set `lastT = null` to avoid spurious or missed alerts. Cards are re-sorted by soonest spawn only when the order string changes; `fitName` shrinks card text when it overflows.

**Audio is fully synthesized** (Web Audio: oscillators/filtered noise through a compressor + generated convolution reverb) — no audio files. Voice announcements use `speechSynthesis` with Russian voices, ranked to prefer male/enhanced ones (`MALE_VOICE`/`GOOD_VOICE`). Audio contexts require a user gesture, hence `unlockAudio()` on first `pointerdown`/start/pause. A Screen Wake Lock is held while a game runs.

**Theming:** day/night toggles `is-day`/`is-night` classes on `<html>` from the game clock; the user light/dark/auto theme is a separate `data-theme` attribute.
