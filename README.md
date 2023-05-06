# cheep8
CHIP-8 emulator/interpreter in Python

## Dependencies
- tk
- pynput

## Issues/Feature wishlist
- Audio support
- GUI to remap controls
- Proper way to restart emulator without relaunching it (also stops user from loading another ROM)
- GUI to change several settings (e.g. screen size/scale, clock speed)
- CLI support
- Port from Tk to Qt

## Development notes
Initial code made in 4 days on a Windows laptop.

### References
- mattmikolay's CHIP‐8 pages: [Technical Reference](https://github.com/mattmikolay/chip-8/wiki/CHIP%E2%80%908-Technical-Reference) and [Instruction Set](https://github.com/mattmikolay/chip-8/wiki/CHIP%E2%80%908-Instruction-Set)
- [CHIP-8 test suite](https://github.com/Timendus/chip8-test-suite) (Tests 4 and 5 helped a lot)

### Tk
I only used Tk because it came built-in with Python for Windows. If I knew it didn't come with Python on Linux (and how ugly it looked there for that matter) I'd probably have used Qt instead.
The method currently used to refresh the display is very slow and scales badly from just increasing the display size. It can only reliably meet the expected 60hz on my machine by disabling the "upscale" (setting `scale` to `1`).

### Variants/quirks
After using the quirks test from the test suite (link in references above) I was under the impression that I could add SCHIP and XO-CHIP support by just providing the options to toggle those specific quirks. Only later that I found [this link] in the test suite readme, containing an extensive list of difference including higher resolution modes, which I'm not interested in supporting at this moment. Either way, that's why I even bothered adding quirk settings and exposing them to the GUI.

### Future plans
Probably not going to work on this anymore, might attempt to port it to Rust at some point, mostly for practice (just started learning it).
