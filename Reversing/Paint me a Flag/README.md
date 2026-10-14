# [Reversing] Paint me a Flag

It was an honor to [paint](https://en.wikipedia.org/wiki/Microsoft_Paint) this flag, I hope you'll enjoy it.

---

## Attachments

- [handout.zip](attachments/handout.zip) ( `paint_me_a_flag`, `flag_part_01..13.png`, `flag_part_01..13.pmaf` )

---

## Solution

`paint_me_a_flag START.png OPS.pmaf OUT.png` applies a list of MS Paint bucket fills (`.pmaf`) to a noise canvas (`.png`). Part 01 runs in ~1 s and gives `Fort`, but parts 02-13 (1600x600, 960000 ops, 64 decoy rounds) would take hours each, so the binary has to be reimplemented.

Each 8-byte record is XORed with a SplitMix64 keystream. Its state depends on the results of the flood fills, so the ops can't be decrypted without simulating them:

```
v     = rec ^ mix(t ^ state)       # pos = v & 0xffffff, colour = v >> 24 & 0xffffff, chk = v >> 48
state = mix(count*C3 ^ mix(hash) ^ state ^ t ^ mix(colour | old << 24))   # (count, hash, old) = fill(pos, colour)
```

The ops are just regions absorbing neighbouring noise pixels (one seed per letter / background piece), the last op of a region sets the real colour (`#16243a` / `#f2eadf`). The binary re-walks the whole growing region on every op, plus 128 decoy fills with random odd colours that never touch the canvas. A union-find storing `(size, xor-hash, colour)` per region returns the same values in O(1), ~3 s per part:

```
$ gcc -O2 -o solve solve.c && python3 run_all.py
Fort | ID{P | 41n7 | _M3_ | L1k3 | _0n3 | _0f_ | Y0ur | _Fr3 | nch_ | Fl4g | zzz! | !!}
```

Final check: every 16-bit record check passes and part 01 is pixel-identical to the original binary's output.

Solver: [solve.c](solve.c), [run_all.py](run_all.py)

---

## Flag

```
FortID{P41n7_M3_L1k3_0n3_0f_Y0ur_Fr3nch_Fl4gzzz!!!}
```