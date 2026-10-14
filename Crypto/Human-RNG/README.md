# [Crypto] Human RNG

You've heard about LCGs, LFSRs, MTs, Xorshifts, RDRANDs, Lavarands... But, can you crack a Human RNG?

---

## Attachments

- [handout.zip](attachments/handout.zip) (`encrypt.py`, `bitstream.txt`, `ciphertext.png`)
- [human_rng_at_work.mp4](attachments/human_rng_at_work.mp4)

---

## Solution

`encrypt.py` builds a QR code of the flag (version 6, ECC level H, mask 0) and XORs its 1681 modules with the last 1681 bits of a bitstream a human typed by hand. `bitstream.txt` only gives the first 1999 bits, so the actual key is redacted. The video is a dead end: no click sound, timing or hand-motion feature matched the known key bits better than chance.

```
key = ciphertext ^ qr(candidate)   # right flag -> ~26% equal neighbours
                                   # wrong flag -> ~45-50% (random baseline 0.437)
```

A QR is also mostly known plaintext the `FortID{` header, `}`, which gives 426 of the 1681 key bits for free. 

```
humans_are_terrible_random_number_generators   # first guess, 44 chars
```

Each candidate costs a few XORs. Brute-forcing word combinations for those 12 chars and scoring block 1 only gives:

```
0.270  humans_are_not_good_random_number_generators   # the only real phrase
0.296  humans_at_or_too_if_random_number_generators
```

Final check all flag decodes correctly with OpenCV.

Solver: [solver.py](solver.py)

---

## Flag

```
FortID{humans_are_not_good_random_number_generators}
```
