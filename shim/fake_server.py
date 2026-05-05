#!/usr/bin/env python3
"""
Fake grading server for a CS:APP-style bomb.

The bomb submits results via HTTP GET to its configured grading host on
port 27054. With the LD_PRELOAD shim redirecting gethostbyname() to
127.0.0.1, those connections land here instead. We reply with 200 OK and
a body of literally "OK" - that's what submitr() compares against.

init_driver() also opens a zero-byte probe connection at startup; we
accept-and-close those with no further handling.
"""
import socket
import threading
import sys
import os

HOST = "127.0.0.1"
# Port the bomb dials. The course-issued bomb hardcodes 27054 (htons(0xae69)
# in init_driver). The demo bomb shipped in this repo uses 12345. Override
# with BOMB_SHIM_PORT when running against a bomb that uses something else.
PORT = int(os.environ.get("BOMB_SHIM_PORT", 27054))
LOGFILE = os.environ.get("BOMB_SHIM_LOG", "shim/submissions.log")

# Headers end with blank line (\r\n\r\n). Body is literally "OK" with NO trailing
# newline - the bomb's rio_readlineb keeps the newline in the buffer, and then
# does strcmp(body, "OK"), which only passes when the line is read-until-EOF.
RESPONSE = b"HTTP/1.0 200 OK\r\n\r\nOK"


def handle(conn, addr):
    try:
        conn.settimeout(2.0)
        data = b""
        while b"\r\n\r\n" not in data and len(data) < 8192:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            data += chunk

        if data:
            try:
                with open(LOGFILE, "ab") as f:
                    f.write(b"--- submission ---\n")
                    f.write(data)
                    if not data.endswith(b"\n"):
                        f.write(b"\n")
            except OSError:
                pass
            conn.sendall(RESPONSE)
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        conn.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(16)
    print(f"[fake grader] listening on {HOST}:{PORT}", file=sys.stderr)
    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        pass
    finally:
        s.close()


if __name__ == "__main__":
    main()
