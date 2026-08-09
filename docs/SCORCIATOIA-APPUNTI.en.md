# The keyboard shortcut that redacts the clipboard

*Questo documento in italiano: [SCORCIATOIA-APPUNTI.md](SCORCIATOIA-APPUNTI.md).*

Copy the text, press the shortcut, paste. What lands is already redacted.

There is nothing to open, upload or download: **the clipboard is the
place**. It exists to remove the friction — open the program, upload the
file, wait, download, copy — which is the real reason a document ends up
inside a chat without passing through here.

## How to use it

1. Select the text and press **Ctrl+C**. From a PDF, from Word, from
   Outlook, from a web page: it makes no difference, it is text on the
   clipboard.
2. Press **Ctrl+Alt+R**.
3. A notification appears: *"9 items redacted · 2 to check"*.
4. Press **Ctrl+V** where you were going. What lands is redacted.

The engine is the same one used for file conversion — same rules, same
arithmetic checks, same tests. There is no second implementation that could
drift.

## What the notification says, and why it matters

A silent transformation is dangerous: with no message you cannot tell "it
worked" from "it did not run". So the notification appears **always**, even
when nothing is found.

The two numbers are not the same thing:

- **redacted** — substituted. That data is no longer on the clipboard.
- **to check** — the **suspects**: the program saw something that
  *resembles* personal data but did not pass its own check, and rather than
  ruin the text it **did not remove it**.

A "to check" greater than zero means something is still on the clipboard
that is worth looking at before pasting. The notification is clickable and
opens the before/after comparison in the program.

## If the redaction removes something you needed

The original stays available for the session: **"Restore the original"** in
the menu of the icon near the clock. It lives **in memory** and is never
written to disk — it disappears when the program closes.

## How to switch it off

From the program, or with the environment variable:

    MR_RAO_SCORCIATOIA=0

The shortcut is changed the same way, for example
`MR_RAO_SCORCIATOIA=ctrl+alt+m` if Ctrl+Alt+R is already taken. If the
combination turns out to be held by another program, Mr. Rao says so at
startup instead of staying quiet and not working.

## Why it is not a keylogger, and how to verify that

A program that stays running and reacts to a key combination has, from the
outside, the same silhouette as a program that records what you type. For a
privacy tool, denying the resemblance in words is not enough, so here is the
technical difference, which anyone can check in the code
(`mr_rao/appunti.py`, AGPL licensed).

**Windows offers two different mechanisms, and we use the restricted one.**

- `SetWindowsHookEx(WH_KEYBOARD_LL)` is a **low-level hook**: the program
  receives **every key** pressed on the machine, and decides what to do with
  it. It is the mechanism you would use to write a keylogger. **Mr. Rao does
  not use it.**
- `RegisterHotKey` declares **one single combination** to Windows. Windows
  watches for it and delivers a message only when *that one* is pressed. The
  program does not see, and cannot see, the other keys. **This is what Mr.
  Rao uses.**

This is not a difference of good intentions: it is a difference in what the
operating system hands to the program. With `RegisterHotKey` the other keys
never arrive at all.

In the same way, **the clipboard is not watched**. There is no periodic
check of its contents: it is opened only when the combination fires, read
once, written once, and closed. Between one key press and the next the
program does not know and cannot know what you copied.

And everything else still holds: **no network** (no request leaves the
machine) and **no disk** (neither the original text nor the redacted one is
written to a file).

## The limit, stated

It still depends on you remembering to press the keys. It removes the
friction, not the decision. Text pasted without pressing anything is
unredacted text, exactly as before.

The engine's limits apply too: what the engine does not recognise it does
not recognise here either, no more and no less than when converting a file.
The declared limits are in [PRIVACY.en.md](PRIVACY.en.md#declared-limits).
