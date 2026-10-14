# [Crypto] Human RNG

You've heard about LCGs, LFSRs, MTs, Xorshifts, RDRANDs, Lavarands... But, can you crack a Human RNG?

---

## Attachments

- [handout.zip](attachments/handout.zip) (`encrypt.py`, `bitstream.txt`, `ciphertext.png`)
- [human_rng_at_work.mp4](attachments/human_rng_at_work.mp4)

---

## Solution

`encrypt.py` builds a QR code of the flag (version 6, ECC level H, mask 0) and XORs its 1681 modules with the last 1681 bits of a bitstream a human typed by hand. `bitstream.txt` only gives the first 1999 bits, so the actual key is redacted. The video is a dead end: no click sound, timing or hand-motion feature matched the known key bits better than chance.

The weak point is the human. People alternate far too much when they try to look random, so neighbouring bits are equal only ~30% of the time (random = 50%). That gives a test for a correct decryption:

```
key = ciphertext ^ qr(candidate)   # right flag -> ~26% equal neighbours
                                   # wrong flag -> ~45-50% (random baseline 0.437)
```

A QR is also mostly known plaintext (finder/timing/alignment patterns, format info, the `FortID{` header, `}`, pad bytes), which gives 426 of the 1681 key bits for free. Version 6-H has 4 Reed-Solomon blocks, and each block's ECC depends only on its own ~15 data bytes, so each block can be scored on its own:

```
humans_are_terrible_random_number_generators   # first guess, 44 chars
block 0: 0.264   block 1: 0.500   block 2: 0.266   block 3: 0.267
```

Blocks 0, 2 and 3 are hot, block 1 is cold, so only chars 7-18 are wrong. QR + RS is affine over GF(2), so each candidate costs a few XORs. Brute-forcing word combinations for those 12 chars and scoring block 1 only gives:

```
0.270  humans_are_not_good_random_number_generators   # the only real phrase
0.296  humans_at_or_too_if_random_number_generators
```

Final check: all four blocks score ~0.26-0.27 and re-encoding the flag decodes correctly with OpenCV.

Solver: [solve.py](solve.py)

---

## Flag

```
FortID{humans_are_not_good_random_number_generators}
```
