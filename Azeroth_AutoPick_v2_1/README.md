# Azeroth AutoPick — The Build Forge v2.1

**A polished Windows-only screen-reading and card-selection companion for Azeroth Survivors.**

This ZIP includes the complete *editable source code*, local OCR, original dark-gold fantasy UI, 27 starting build profiles across nine classes, a class spell/jewellery codex, card-border recognition, safer decision automation, a run-action ledger, a guide, sample screenshot fixtures and offline tests.

## v2.1: IMPORTANT FIX — attachment from the app window

The v2.0 **ATTACH GAME** button could attach to **Azeroth AutoPick itself**, because clicking the button made AutoPick the focused window, and the old title check accepted its own word "Azeroth". This is the exact failure shown by the user screenshot: `Attached: Azeroth AutoPick — The Build Forge v2`. In v2.1 that is explicitly prohibited.

1. Open **Azeroth Survivors** and launch Build Forge.
2. Click **ATTACH GAME** within Build Forge. It now searches visible Windows windows, checks process executable names and window titles, and attaches to the real game **even though Build Forge is in front**. If multiple genuine game windows are found, select the correct one from the pop-up. Alternatively focus the actual game and press **F8**.
3. Verify the event log says **`Attached: Azeroth Survivors`** (or another actual game-window name), not `Attached: Azeroth AutoPick`.
4. Click **PREVIEW CHOICES** with the level-up cards visible. The Build Forge window hides during OCR and comes back **after** the scan completes; you should see three names or a specific no-choice reason.
5. Click **AUTO ON / OFF**, or press **F9** while in the game. **`AUTO ARMED · CLICK GAME TO ACT` is an enabled-but-not-active state, not an error**: it waits for the attached game to have keyboard/mouse focus. Bring the game to the front and the status becomes **`AUTO ACTIVE`**. If the three cards do not match your build, check the reason in the Strategy Verdict; it may reroll free, skip, or wait safely.
6. **F10** is the immediate stop key.

**If the event log says GAME NOT FOUND:** No confidently identifiable game was found. Focus the game and press F8, or check that the executable/title actually includes "Azeroth Survivors" or "World of Warcraft". AutoPick does not attach itself or a random browser/desktop window when it cannot identify the real game. If the game still has an unfamiliar executable/window name, the window-recognition code may need a verified name rather than a guessed one.

**Note:** The application still only reads cards from the visible game screen and only sends automatic input while the selected game window is in the foreground. If it's covered by another program during gameplay, auto input is paused. This is intentional.

## Start here — Windows

1. Extract the *entire* ZIP into its own folder. Do not run a `.bat` file directly from inside the ZIP.
2. Install **64-bit Python 3.11 or 3.12** from https://www.python.org/downloads/windows/ and tick **Add python.exe to PATH**. Python is needed because this is a source distribution, not a signed `.exe` installer.
3. Double-click **`start_windows.bat`**. On the first launch it installs its Python dependencies into a private `.venv` folder. Later launches reuse the environment.
4. Open **Azeroth Survivors** on the same Windows desktop, ideally in **windowed or borderless-window mode**. Select a class and one of three build styles in the left sidebar.
5. Click **SAVE BUILD** or edit spell order, passives, jewellery targets, avoid lists and banish lists in **BUILD FORGE**. Use **TACTICS** to set rarity floors and free-reroll rules.
6. Click **ATTACH GAME** in the app (v2.1 detects the real window), or focus the game and press **F8**. **F7** previews without clicks. **F9** arms automatic card selection, **F10** stops it. Switch back into the game after arming.
7. **Start in preview mode**. Inspect the OCR results and proposed choices before enabling actual keyboard/mouse input.

### Keys

| Key | Meaning |
| --- | --- |
| F8 | Attach to the game window, using direct focus or secure game discovery (automation stays off) |
| F7 | Scan once in preview mode without input |
| F9 | Arm/disarm automatic choice input |
| F10 | Stop automatic input |

The game has the usual **1–3 (or 1–4)** numerical card choices, **R** free reroll and **X** skip keyboard shortcuts in the supplied game screenshots. Both the actual game shortcuts and the auto-action behaviour **must be checked in your installed game version**; not every screen or build may behave the same. Banish buttons are located by their visible text and clicked, not by hard-coded XY coordinates.

## Main features

- **No repeated calibration**: automatically detects the visible borders of three- or four-card choice screens. If screen geometry is uncertain, it does *not* press a key.
- **9 classes, 27 editable starting strategies**: 3 archetypes per class, six requested active spells each, optional advisory passives, jewellery priorities and defensive / offensive synergy tags.
- **Full starting catalogue**: 104 class-spell entries, 9 rings, 14 trinkets, 20 general/shared amulets, 15 separate named legendary spell-amulet families (58 distinct jewellery entries). Includes spell-to-family reference information.
- **Conditional scoring**: priority order, card rarity, rank upgrades, synergy and relative value. An explicit rarity floor means you can reject a desired Common or Uncommon card rather than taking it blindly.
- **Free rerolls only**: verifies both the **numeric free reroll counter** and the button's visual gold/red presentation before pressing **R**. NEVER automatically buys rerolls with gold; if exhausted, skip with **X** when visible and permitted.
- **Banish safeguards**: only banishes explicitly blacklisted jewellery, only if no acceptable target exists, and stops at your configurable total. It does not intentionally waste a banish on a screen with a desirable choice.
- **Equipment protection**: conservatively tracks *inferred* rings, trinkets and current amulet based on choices the app sent, and avoids replacing protected slots. Because this does **not** read the game's true inventory, changes you make manually may make the inferred ledger stale.
- **Legendary variant caution**: certain legendary family names apply to multiple spells. A family title alone is not sufficient to prove which spell it modifies. By default the app requires readable card-description evidence of a planned spell before equipping it; otherwise it rerolls or skips safely. You can change `verify_legendary_variant` in `settings.json` if you choose to take that risk.
- **Run ledger and CSV**: local log of issued/acknowledged actions; manually acquired items and true server state cannot be known reliably.
- **Safety**: only acts on the focused attached window, waits for the display to change before another selection, halts if an action seems stuck, has an emergency stop key, runs offline after initial package installation, and never asks for game account credentials.

## Why it is not a trained AI or a native game add-on

It is an **auditable rules-based strategy and OCR engine**, *not* a machine-learned agent or verified mathematical optimiser. It has no access to the closed-source Azeroth Survivors live server, unpublished probabilities, all gear affixes, exact personal talent allocations or the real random outcome of a reroll. The documented 1.12.1 addon `AZS_*` API supports read-only run information but no supported direct `pick card` operation. The companion therefore watches the visible game screen and sends normal local keyboard/mouse input. There is no memory injection, packet manipulation or server access.

It **cannot automatically choose character creation, talents, equipment changes outside card popups, arena entry or every game's menus**. The suggested talent capstones and passives are advisory notes. No build is guaranteed best. This is a fully packaged *source project* with a broad implementation and offline tests, not proof of compatibility with every future game release.

## Reliability and screen support

The card-border detector and free/paid reroll colour guard were checked against the **two supplied 2048×1280 Paladin screenshots** in `/fixtures`. The OCR game-reading dependency and input controls are **not live-tested on a Windows game installation** here; treat the first real session as validation and use F7 preview. Jewellery screens, other scaling factors, localisation, anti-automation restrictions and future updates may require code changes. The app intentionally **does nothing** when a necessary detail cannot be verified.

Some choices are rendered differently or may use 4 cards. The engine supports both but the original screenshot validation covers the 3-card level-up screen. At resolutions or language settings where text reading fails, the safe outcome is no input—not blind clicks.

A game or server may prohibit third-party automation. Check its rules and use at your own discretion.

## Files

| File or directory | Purpose |
| --- | --- |
| `main.py` | Full fantasy-style 6-tab control panel, editor, run ledger and hotkeys |
| `autopick/advanced.py` | Risk-controlled strategy engine and inferred equipment |
| `autopick/vision.py`, `layout.py`, `visual.py` | Auto-layout, OCR routing, reroll visual check |
| `autopick/catalog.py`, `amulets.py`, `guides.py` | Local class and jewellery knowledge base + guide notes |
| `autopick/capture.py` | Local Windows foreground capture and OCR wrapper |
| `profiles.json` | Editable starting builds; saved in-place after editing |
| `settings.json` | Preset policy and GUI settings |
| `fixtures/` | User-provided regression screenshots for offline layout tests |
| `tests/` | Tests, including simulated OCR and screen-geometry checks |
| `interface_preview.png` | Preview of *the app UI*, not a gameplay screenshot |

To run source tests on a developer machine with Python installed: `python -m pip install pytest numpy Pillow` then `python -m pytest -q`. The normal Windows launcher handles the runtime requirements.

## Reference material and scope

- Community-provided class, spell, and jewellery names: https://github.com/cadoky/ASBuilder (Data.lua, November 2026 snapshot).
- Community talent/build guide notes: https://azerothsurvivorsgame.com/builds/ — editorial suggestions, not copied simulation results.
- Azeroth Survivors documented addon API: https://github.com/migwynkriid13/SurvivorsDragonUi/blob/main/docs/AzerothSurvivors-Addon-API-2026-10-15.txt

These sources may evolve. Their availability does **not** mean proprietary game source code is open-source or that all mechanics are publicly verifiable.

## Data privacy and uninstall

The app performs **no network requests** while running. OCR takes local screenshots in memory and processes them with local packages. Run ledger exports are written on your computer. The ZIP ships no downloader for game files, no injected DLLs and no user-specific data. To uninstall, close the program and delete its extracted folder (including `.venv`).
