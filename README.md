# Bomb Lab local-run harness

An `LD_PRELOAD` shim and a loopback HTTP grader that let a CS:APP-style bomb
binary run on a machine that isn't the course server.

Only the shim, the server, and the glue live in this repository. The bomb
binary, the write-up, and anything that identifies a specific bomb instance
(userid, submission logs) are either gitignored or externalized to a `.env`
file. Bring your own bomb.

## What this does

The bomb normally:

1. Calls `gethostname()` and aborts unless the result matches a userid that
   is baked into its `.data` section.
2. Resolves a course-server hostname and opens a TCP probe to port 27054.
3. After every phase is defused or detonated, submits the outcome as an
   HTTP/1.0 GET request to the same host.

This harness intercepts all three:

- The shim overrides `gethostname()` to return `$BOMB_USERID`.
- The shim overrides `gethostbyname()` to resolve any name to `127.0.0.1`.
- `shim/fake_server.py` listens on `127.0.0.1:27054` and answers every
  request with `HTTP/1.0 200 OK\r\n\r\nOK` (no trailing newline — that is
  load-bearing; the bomb's `rio_readlineb` preserves the newline in the
  buffer and then `strcmp`s the body against a literal `"OK"`).

Nothing in the bomb binary is patched.

## Prerequisites

- Linux with `gcc`, `make`, `python3`, and `ss` (from `iproute2`).
- Your bomb binary, placed at the project root as `./bomb`.

## Setup

1. Copy the env template:

   ```sh
   cp .env.example .env
   ```

2. Open `.env` and set `BOMB_USERID` to match the userid baked into your
   bomb. You can find it with any of:

   ```sh
   strings bomb | head
   objdump -t bomb | grep '\buserid\b'        # gives the address
   objdump -s -j .data bomb | less            # look at that address
   ```

   The hostcheck is `strcasecmp`-based, so case does not matter, but the
   value must otherwise be exact.

3. Drop your bomb binary at `./bomb`:

   ```sh
   cp /path/to/your/bomb ./bomb
   chmod +x ./bomb
   ```

## Running

```sh
./run.sh                   # interactive
./run.sh solutions.txt     # batch: one phase answer per line
```

`run.sh` will:

- source `.env` with auto-export so the shim sees `BOMB_USERID`
- build `shim/libbombshim.so` if it is missing or out of date
- start `shim/fake_server.py` on `127.0.0.1:27054` if nothing is listening
- launch the bomb with `LD_PRELOAD` pointing at the shim

Submissions the bomb tries to send are appended to `shim/submissions.log`
(gitignored) so you can see exactly what would have gone upstream.

## Files

- `shim/shim.c`, `shim/Makefile` — the `LD_PRELOAD` library.
- `shim/fake_server.py` — the loopback grader.
- `run.sh` — wrapper that orchestrates everything.
- `.env.example` — template for credentials.
- `.gitignore` — keeps the bomb, build output, `.env`, submission logs, and
  the write-up out of commits.

## Security notes

- **Do not commit `.env`**. It is in `.gitignore`; keep it that way. The
  hostname check is trivially reversible, so `BOMB_USERID` alone is not
  catastrophic to leak, but it ties commits to a specific student.
- **Do not commit `bomb`**. The bomb binary contains a `user_password`
  string in `.data` that the official submission endpoint treats as proof
  of identity.
- **Do not commit `shim/submissions.log`**. Each line is a full HTTP GET
  including `userid=` and `userpwd=` in the query string, verbatim.
- The fake grader binds only on `127.0.0.1`, so it is not reachable off-box
  by default. Keep it that way unless you have a specific reason otherwise.

## Why port 27054?

It is not configurable. The port is `htons(0xae69)` in the bomb's
`init_driver`, and changing it would require patching the binary. The fake
server matches what the bomb expects.
