#!/usr/bin/env python3
"""Human RNG - solver.
Usage: python3 solve.py [ciphertext.png]
Needs: numpy, pillow (opencv optional, only for the final sanity decode).
"""
import sys, re, itertools
import numpy as np
from PIL import Image

# ---------------------------------------------------------------- QR v6-H builder

SIZE=41; VER=6
# GF(256)
EXP=[0]*512; LOG=[0]*256
x=1
for i in range(255):
    EXP[i]=x; LOG[x]=i; x<<=1
    if x&0x100: x^=0x11D
for i in range(255,512): EXP[i]=EXP[i-255]
def gmul(a,b):
    return 0 if a==0 or b==0 else EXP[LOG[a]+LOG[b]]
def rs_gen(n):
    g=[1]
    for i in range(n):
        ng=[0]*(len(g)+1)
        for j,c in enumerate(g):
            ng[j]^=c
            ng[j+1]^=gmul(c,EXP[i])
        g=ng
    return g
GEN=rs_gen(28)
def rs_ec(data,n=28):
    res=[0]*n
    for d in data:
        f=d^res[0]
        res=res[1:]+[0]
        if f:
            for i in range(n):
                res[i]^=gmul(GEN[i+1],f)
    return res
def bch(d):
    def dig(x): return x.bit_length()
    G15=0x537
    r=d<<10
    while dig(r)-dig(G15)>=0:
        r^=G15<<(dig(r)-dig(G15))
    return (d<<10)|r
def fmt_bits(): return bch((2<<3)|0)^0x5412
def func_matrix():
    m=[[None]*SIZE for _ in range(SIZE)]
    def finder(r,c):
        for dr in range(-1,8):
            for dc in range(-1,8):
                rr,cc=r+dr,c+dc
                if 0<=rr<SIZE and 0<=cc<SIZE:
                    if 0<=dr<=6 and (dc in(0,6)) or 0<=dc<=6 and (dr in(0,6)) or (2<=dr<=4 and 2<=dc<=4):
                        m[rr][cc]=1
                    else: m[rr][cc]=0
    finder(0,0);finder(SIZE-7,0);finder(0,SIZE-7)
    # alignment at 34,34
    for dr in range(-2,3):
        for dc in range(-2,3):
            m[34+dr][34+dc]=1 if (max(abs(dr),abs(dc))!=1) else 0
    for i in range(8,SIZE-8):
        if m[6][i] is None: m[6][i]=1 if i%2==0 else 0
        if m[i][6] is None: m[i][6]=1 if i%2==0 else 0
    bits=fmt_bits()
    for i in range(15):
        mod=(bits>>i)&1
        if i<6: m[i][8]=mod
        elif i<8: m[i+1][8]=mod
        else: m[SIZE-15+i][8]=mod
        if i<8: m[8][SIZE-i-1]=mod
        elif i<9: m[8][15-i-1+1]=mod
        else: m[8][15-i-1]=mod
    m[SIZE-8][8]=1
    return m
def data_positions():
    f=func_matrix()
    pos=[]  # list of (r,c) in codeword-bit order
    inc=-1;row=SIZE-1
    for col in range(SIZE-1,0,-2):
        if col<=6: col-=1
        while True:
            for c in (col,col-1):
                if f[row][c] is None: pos.append((row,c))
            row+=inc
            if row<0 or SIZE<=row:
                row-=inc;inc=-inc;break
    return f,pos
def codewords(databytes):
    assert len(databytes)==60
    blocks=[databytes[i*15:(i+1)*15] for i in range(4)]
    ecs=[rs_ec(b) for b in blocks]
    out=[]
    for i in range(15):
        for b in blocks: out.append(b[i])
    for i in range(28):
        for e in ecs: out.append(e[i])
    return out
def data_stream(flag):
    s=flag.encode()
    bits=[]
    def put(v,n):
        for i in range(n-1,-1,-1): bits.append((v>>i)&1)
    put(4,4);put(len(s),8)
    for ch in s: put(ch,8)
    for _ in range(min(4,480-len(bits))): bits.append(0)
    while len(bits)%8: bits.append(0)
    by=[int(''.join(map(str,bits[i:i+8])),2) for i in range(0,len(bits),8)]
    pads=[0xEC,0x11];i=0
    while len(by)<60: by.append(pads[i%2]);i+=1
    return by
def build(flag):
    f,pos=data_positions()
    cw=codewords(data_stream(flag))
    bits=[]
    for b in cw:
        for i in range(7,-1,-1): bits.append((b>>i)&1)
    bits+= [0]*(len(pos)-len(bits))
    m=[[(f[r][c] if f[r][c] is not None else 0) for c in range(SIZE)] for r in range(SIZE)]
    for (r,c),b in zip(pos,bits):
        if (r+c)%2==0: b^=1
        m[r][c]=b
    return m
def flat(m): return [m[r][c] for r in range(SIZE) for c in range(SIZE)]


# ---------------------------------------------------------------- attack
path = sys.argv[1] if len(sys.argv) > 1 else 'ciphertext.png'
a = np.array(Image.open(path).convert('L'))
ct = np.array([1 if a[y*10+5, x*10+5] < 128 else 0 for y in range(41) for x in range(41)])

# which RS block (0..3) owns every module; the ECC of a block depends ONLY on that block's 15 data bytes
fmap, pos = data_positions()
owner = -np.ones(1681, int)
for sb, (r, c) in enumerate(pos):
    by = sb // 8
    owner[r*41 + c] = by % 4 if by < 60 else (by - 60) % 4
PAIRS = {b: np.array([i for i in range(1, 1681) if owner[i] == b and owner[i-1] == b]) for b in range(4)}

def block_scores(body):
    """fraction of equal neighbours in key = ct ^ qr(body), per block.
    Right guess -> ~0.26 (human alternates a lot).  Wrong guess -> ~0.45-0.50."""
    key = ct ^ np.array(flat(build('FortID{' + body + '}')))
    return [float((key[p] == key[p-1]).mean()) for p in (PAIRS[b] for b in range(4))]

def show(body):
    print(f'{body!r:60} ', [round(s, 3) for s in block_scores(body)])

print('[*] crib / guess:')
show('humans_are_terrible_random_number_generators')   # blocks 0,2,3 light up, block 1 does not

# block 1 only covers chars 7..20, so search just those 12 unknown chars (positions 7..18)
LEFT, RIGHT = 'humans_', '_random_number_generators'
words = ('a an the is are was be it of to in on at by for with as or and not no so if we you they all any some '
         'many most more very too such just only even still also really truly actually bad good poor best worst '
         'great terrible horrible awful weak strong random number generator generators predictable biased human '
         'humans people machine can could would will cannot know guess crack cracked break hard easy secure safe '
         'fair lazy smart dumb real fake true false right wrong bits key seed state').split()
bylen = {}
for w in set(words): bylen.setdefault(len(w), []).append(w)

def combos(rem):
    for L in range(1, rem + 1):
        for w in bylen.get(L, []):
            if rem == L: yield w
            elif rem - L - 1 >= 1:
                for rest in combos(rem - L - 1): yield w + '_' + rest

print('[*] searching the 12-char middle, scoring block 1 only ...')
# QR (data + RS ECC) is affine over GF(2): qr(body) = qr(base) ^ XOR_j delta[j, body[j]]  -> candidates cost one XOR each
SYM = 'abcdefghijklmnopqrstuvwxyz_'
BASE = LEFT + 'a' * 12 + RIGHT
base = np.array(flat(build('FortID{' + BASE + '}')))
delta = {(j, ch): np.array(flat(build('FortID{' + BASE[:j] + ch + BASE[j+1:] + '}'))) ^ base
         for j in range(7, 19) for ch in SYM}
k0 = ct ^ base
P1, P1m = PAIRS[1], PAIRS[1] - 1
def fast_score(m):
    k = k0.copy()
    for j, ch in enumerate(m): k ^= delta[(7 + j, ch)]
    return float((k[P1] == k[P1m]).mean())
best = sorted((fast_score(m), m) for m in set(combos(12)))[:5]
for sc, m in best: print(f'    {sc:.3f}  {LEFT + m + RIGHT}')

body = LEFT + best[0][1] + RIGHT
print('[*] full check:'); show(body)
flag = 'FortID{' + body + '}'
print('[+] flag:', flag)

try:  # sanity: our encoder really produces a scannable QR containing the flag
    import cv2
    m = np.array(flat(build('FortID{' + body + '}'))).reshape(41, 41)
    img = np.kron(1 - m, np.ones((8, 8))).astype(np.uint8) * 255
    img = np.pad(img, 32, constant_values=255)
    print('[*] cv2 decode of re-encoded QR:', cv2.QRCodeDetector().detectAndDecode(img)[0])
except Exception as e:
    print('[-] cv2 sanity check skipped:', e)
