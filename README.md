# Bomb Lab local-run harness

An `LD_PRELOAD` shim and a loopback HTTP grader that let a CS:APP-style bomb
binary run on a machine that isn't the course server.

Only the shim, the server, and the glue live in this repository. The bomb
binary, the write-up, and anything that identifies a specific bomb instance
(userid, submission logs) are either gitignored or externalized to a `.env`
file. Bring your own bomb.

A standalone **demo bomb** lives under [`demo-bomb/`](demo-bomb/) so the
harness can be exercised end-to-end without a real course-issued binary.
It is **not** the bomb that the [blog post](blog.md) walks through — that
one stays out of the repo for the reasons listed in *Security notes*. The
demo bomb is built from the open CS:APP sources (Bryant & O'Hallaron) with
fake server/userid values baked in, and exists purely so a reader can see
the shim and fake grader work. See [Demo bomb](#demo-bomb) below.

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
  macOS won't work as-is — `LD_PRELOAD` is glibc-specific, and Apple's
  `DYLD_INSERT_LIBRARIES` equivalent is blocked by SIP for most binaries.
- A bomb binary at the project root as `./bomb`. If you don't have one,
  use the [demo bomb](#demo-bomb) shipped in this repo.

## Setup

`.env.example` ships pre-configured for the [demo bomb](#demo-bomb), so
the fastest path to seeing the harness work end-to-end on a fresh clone is:

```sh
cp .env.example .env
cp demo-bomb/bomb ./bomb
./run.sh demo-bomb/solution.txt
```

### Switching to your own bomb

1. Copy the env template if you haven't already:

   ```sh
   cp .env.example .env
   ```

2. Edit `.env`:
   - Set `BOMB_USERID` to the hostname your bomb's `initialize_bomb()`
     expects. Despite the variable name, this is what the shim makes
     `gethostname()` return — for a course-issued bomb that value
     happens to equal the `userid` string baked into `.data`. Recover it
     from your binary with:

     ```sh
     strings bomb | head
     objdump -t bomb | grep '\buserid\b'        # gives the address
     objdump -s -j .data bomb | less            # look at that address
     ```

     The hostcheck is `strcasecmp`-based, so case does not matter, but
     the value must otherwise be exact.
   - Comment out `BOMB_SHIM_PORT` so the course-default `27054` is used.

3. Drop your bomb binary at `./bomb`:

   ```sh
   cp /path/to/your/bomb ./bomb
   chmod +x ./bomb
   ```

## Running

```sh
./run.sh                   # interactive: type each phase answer at the prompt
./run.sh solutions.txt     # batch: one answer per line, in order
```

Solutions-file format: one phase answer per line, phase 1 on line 1
through phase 6 on line 6. To also arm the secret phase, end phase 4's
line with a space and the literal string `DrEvil`, and put the secret
phase's answer on line 7. See [`demo-bomb/solution.txt`](demo-bomb/solution.txt)
for a worked example.

`run.sh` will:

- source `.env` with auto-export so the shim sees `BOMB_USERID`
- build `shim/libbombshim.so` if it is missing or out of date
- start `shim/fake_server.py` on `127.0.0.1:$BOMB_SHIM_PORT` (defaulting
  to `27054`) if nothing is listening on that port already
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

It is not configurable *in the bomb*. The port is `htons(0xae69)` in the
course-issued bomb's `init_driver`, and changing it would require patching
the binary. The fake server defaults to `27054` to match.

If you happen to be running a bomb that uses a different port (the demo
bomb in this repo uses `12345`), set `BOMB_SHIM_PORT` in `.env` and both
`fake_server.py` and `run.sh` will pick it up.

## Demo bomb

[`demo-bomb/bomb`](demo-bomb/bomb) is a self-contained, **non-course**
binary built from the public CS:APP bomb sources with deliberately fake
values:

- `host_table[]`: `demohost.changeme.edu`, `demohost`, `localhost`
- baked-in `userid`: `demouser`
- grading host:port: `changeme.edu:12345`
- `bomb_id`: `1`, `LABID`: `f12`
- phase variants: `aaaaaa` (deterministic, so the canonical solution is
  always the one in [`demo-bomb/solution.txt`](demo-bomb/solution.txt))

Nothing in it ties to a real student or a real grading server, and the
solution is committed alongside it. **It is a demonstration target for the
shim, nothing more.** If you want to actually solve a bomb the way the
blog post describes, drop your own course-issued binary at `./bomb`; the
demo bomb under `demo-bomb/` is independent of that path.

To run it (the shipped `.env.example` is already configured for this
case — back up any existing `.env` first if you have one, since `cp`
will overwrite it):

```sh
cp .env.example .env
cp demo-bomb/bomb ./bomb
./run.sh demo-bomb/solution.txt
```

Expected output ends with:

```
Curses, you've found the secret phase!
But finding it and solving it are quite different...
Wow! You've defused the secret stage!
Congratulations! You've defused the bomb!
Your instructor has been notified and will verify your solution.
```

`shim/submissions.log` will then contain seven `GET /csapp/submitr.pl/...`
lines (one per defused phase + secret), all carrying `userid=demouser`.
