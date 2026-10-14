// solve.c - fast, exact re-implementation of ./paint_me_a_flag
//
//   gcc -O2 -o solve solve.c
//   ./solve START.rgb OPS.pmaf OUT.rgb     (raw 8-bit RGB = W*H*3 bytes; W,H come from the .pmaf header)
//
// .pmaf = 40-byte header: "PMAF\x03\r\n\x1a" | u32 W | u32 H | u64 count | u64 seed | u32 rounds | u32 0
//         followed by `count` encrypted 8-byte records.
// For record idx (t = idx*GAMMA, mix = SplitMix64 finaliser):
//    v   = rec ^ mix(t ^ state)       pos = v & 0xffffff, colour = (v>>24) & 0xffffff, chk = v >> 48
//    chk must equal mix((v & 0xffffffffffff) ^ t ^ state) >> 48          (integrity check)
//    (a,b,c) = fill(pos, colour)      a=|region|, b=XOR of mix(p ^ KH) over region, c=old colour
//    state   = mix(a*C3 ^ mix(b) ^ state ^ t ^ mix(colour | c<<24))
//    then `rounds` decoy rounds: fill(pos, rc) / fill(pos, colour) with a pseudo-random odd colour rc.
//
// The original re-runs a BFS over the whole growing region for every op (plus 128 decoy fills),
// i.e. hours. Here regions live in a union-find holding (size, xor-hash, colour): ~O(1) per fill.
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>

typedef uint64_t u64; typedef uint32_t u32; typedef uint8_t u8;

#define GAMMA 0x9e3779b97f4a7c15ULL
#define C3    0xd6e8feb86659fd93ULL
#define KH    0x243f6a8885a308d3ULL
#define BAD   0xf2eadfu
#define NIL   0xffffffffu

static inline u64 mix(u64 z){
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

static u32 W, H, N;
static u32 *par, *sz, *colr, *nxt, *cand, *chead, *cprv, *cnx;   /* per-pixel / per-root arrays */
static u64 *xh;

static u32 find(u32 x){
    u32 r = x; while (par[r] != r) r = par[r];
    while (par[x] != r){ u32 n = par[x]; par[x] = r; x = n; }
    return r;
}
/* per-colour list of component roots */
static void cins(u32 r, u32 c){ u32 h = chead[c]; cprv[r] = NIL; cnx[r] = h; if (h != NIL) cprv[h] = r; chead[c] = r; }
static void crem(u32 r, u32 c){ u32 p = cprv[r], n = cnx[r]; if (p != NIL) cnx[p] = n; else chead[c] = n; if (n != NIL) cprv[n] = p; }

static u32 unite(u32 a, u32 b){                 /* a,b: distinct roots with the same colour */
    if (sz[a] < sz[b]){ u32 t = a; a = b; b = t; }
    crem(b, colr[b]);
    par[b] = a; sz[a] += sz[b]; xh[a] ^= xh[b];
    u32 t = nxt[a]; nxt[a] = nxt[b]; nxt[b] = t;   /* splice circular member lists */
    return a;
}
static int adjacent(u32 A, u32 B){              /* are two components touching? scan the smaller one */
    if (sz[A] > sz[B]){ u32 t = A; A = B; B = t; }
    u32 p = A;
    do {
        u32 x = p % W, y = p / W;
        if (x > 0   && find(p - 1) == B) return 1;
        if (x < W-1 && find(p + 1) == B) return 1;
        if (y > 0   && find(p - W) == B) return 1;
        if (y < H-1 && find(p + W) == B) return 1;
        p = nxt[p];
    } while (p != A);
    return 0;
}
/* what the binary's flood fill returns for (pos, nc), then recolour the region and merge with neighbours of colour nc */
static void fill(u32 pos, u32 nc, u64 *a, u64 *b, u32 *c){
    u32 r = find(pos), old = colr[r];
    *a = sz[r]; *b = xh[r]; *c = old;
    if (old == nc) return;
    u32 n = 0;
    for (u32 q = chead[nc]; q != NIL; q = cnx[q]) cand[n++] = q;
    crem(r, old); colr[r] = nc; cins(r, nc);
    u32 cur = r;
    for (u32 i = 0; i < n; i++) if (adjacent(cur, cand[i])) cur = unite(cur, cand[i]);
}

int main(int argc, char **argv){
    if (argc != 4){ fprintf(stderr, "usage: %s START.rgb OPS.pmaf OUT.rgb\n", argv[0]); return 2; }
    FILE *f = fopen(argv[2], "rb"); if (!f){ perror(argv[2]); return 2; }
    fseek(f, 0, SEEK_END); long fs = ftell(f); fseek(f, 0, SEEK_SET);
    u8 *buf = malloc(fs); if (fread(buf, 1, fs, f) != (size_t)fs) return 2; fclose(f);
    if (fs < 40 || memcmp(buf, "PMAF\x03\r\n\x1a", 8)){ fprintf(stderr, "not a PMAF file\n"); return 2; }
    u32 rounds; u64 count, seed;
    memcpy(&W, buf + 8, 4); memcpy(&H, buf + 12, 4); memcpy(&count, buf + 16, 8);
    memcpy(&seed, buf + 24, 8); memcpy(&rounds, buf + 32, 4);
    N = W * H;
    if ((u64)fs != 40 + count * 8){ fprintf(stderr, "size mismatch\n"); return 2; }

    f = fopen(argv[1], "rb"); if (!f){ perror(argv[1]); return 2; }
    u8 *rgb = malloc((size_t)N * 3);
    if (fread(rgb, 1, (size_t)N * 3, f) != (size_t)N * 3){ fprintf(stderr, "START.rgb has the wrong size\n"); return 2; }
    fclose(f);

    par = malloc(N * 4); sz = malloc(N * 4); colr = malloc(N * 4); nxt = malloc(N * 4);
    cprv = malloc(N * 4); cnx = malloc(N * 4); cand = malloc(N * 4 + 16); xh = malloc((size_t)N * 8);
    chead = malloc((size_t)(1u << 24) * 4); memset(chead, 0xff, (size_t)(1u << 24) * 4);
    for (u32 p = 0; p < N; p++){
        par[p] = p; sz[p] = 1; nxt[p] = p; xh[p] = mix((u64)p ^ KH);
        colr[p] = ((u32)rgb[3*p] << 16) | ((u32)rgb[3*p+1] << 8) | rgb[3*p+2];
        cins(p, colr[p]);
    }

    u64 state = mix( mix(count) ^ seed ^ (u64)H ^ ((u64)W << 32) ^ ((u64)rounds * C3) ^ 0x6f3d9b21a4c875e1ULL );
    u64 t = 0;
    for (u64 idx = 0; idx < count; idx++, t += GAMMA){
        u64 raw; memcpy(&raw, buf + 40 + idx * 8, 8);
        u64 v = raw ^ mix(t ^ state);
        u32 pos = (u32)(v & 0xffffff), colour = (u32)((v >> 24) & 0xffffff);
        if ((v >> 48) != (mix((v & 0xffffffffffffULL) ^ t ^ state) >> 48)){
            fprintf(stderr, "lost sync at op %llu\n", (unsigned long long)idx); return 3; }
        if (pos >= N){ fprintf(stderr, "position outside canvas at op %llu\n", (unsigned long long)idx); return 3; }

        u64 a, b; u32 c;
        fill(pos, colour, &a, &b, &c);
        state = mix( a*C3 ^ mix(b) ^ state ^ t ^ mix((u64)colour | ((u64)c << 24)) );

        if (rounds){
            u32 r1 = find(pos);
            u64 A3 = (u64)sz[r1] * C3, mixB = mix(xh[r1]), jc = 0;
            for (u32 j = 1; j <= rounds; j++){
                jc += C3;
                u64 d = t ^ state ^ jc;
                u32 rc = (u32)(mix(d) & 0xfffffe) | 1;
                while (rc == BAD){ d = mix(d + GAMMA); rc = (u32)(mix(d) & 0xfffffe) | 1; }
                if (rc != colour && chead[rc] != NIL){          /* rare: decoy colour already on canvas -> do it for real */
                    u64 a1, b1, a2, b2; u32 c1, c2;
                    fill(pos, rc, &a1, &b1, &c1);
                    state = mix( a1*C3 ^ mix(b1) ^ state ^ t ^ mix((u64)rc | ((u64)c1 << 24)) );
                    fill(pos, colour, &a2, &b2, &c2);
                    state = mix( a2*C3 ^ mix(b2) ^ t ^ mix((u64)colour | ((u64)c2 << 24)) ^ state );
                    r1 = find(pos); A3 = (u64)sz[r1] * C3; mixB = mix(xh[r1]);
                } else {                                         /* decoy fills never change the canvas */
                    state = mix( A3 ^ mixB ^ state ^ t ^ mix((u64)rc | ((u64)colour << 24)) );
                    u32 c2 = (rc == colour) ? colour : rc;
                    state = mix( A3 ^ mixB ^ t ^ mix((u64)colour | ((u64)c2 << 24)) ^ state );
                }
            }
        }
    }

    FILE *o = fopen(argv[3], "wb"); if (!o){ perror(argv[3]); return 2; }
    for (u32 p = 0; p < N; p++){
        u32 cc = colr[find(p)];
        u8 px[3] = { (u8)(cc >> 16), (u8)(cc >> 8), (u8)cc };
        fwrite(px, 1, 3, o);
    }
    fclose(o);
    fprintf(stderr, "  ok: %llu ops decoded, every integrity check passed\n", (unsigned long long)count);
    return 0;
}
