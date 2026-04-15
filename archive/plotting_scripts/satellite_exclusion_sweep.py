#!/usr/bin/env python3
import math
import os
import subprocess
from collections import Counter

RINEX = 'logger/2/gnss_log_2026_03_15_11_10_23.26o'
RTKLIB_EXE = r'C:\\tools\\RTKLIB_EX_2.5.0\\rnx2rtkp.exe'
WORKDIR = r'C:\\Users\\Guntesh\\Desktop\\foo\\gsd'
BASE_FILES = [
    'logger\\2\\gnss_log_2026_03_15_11_10_23.26o',
    'cors\\Order2\\HYDE074F00.26o',
    'cors\\Order2\\HYDE074F00.26n',
    'cors\\Order2\\HYDE074F00.26g',
    'cors\\Order2\\HYDE074F00.26l',
    'cors\\Order2\\HYDE074F00.26c',
    'cors\\Order2\\HYDE074F00.26j',
]


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def metrics(path):
    rows = []
    with open(path, 'r') as f:
        for line in f:
            if line.startswith('%') or not line.strip():
                continue
            p = line.split()
            rows.append((float(p[2]), float(p[3])))
    if len(rows) < 2:
        return None

    steps = [
        haversine(rows[i - 1][0], rows[i - 1][1], rows[i][0], rows[i][1])
        for i in range(1, len(rows))
    ]
    steps_sorted = sorted(steps)
    return {
        'n': len(rows),
        'mean': sum(steps) / len(steps),
        'p95': steps_sorted[int(0.95 * len(steps)) - 1],
        'max': max(steps),
        'gt3': sum(1 for s in steps if s > 3.0),
        'gt5': sum(1 for s in steps if s > 5.0),
    }


def collect_candidates(rinex_path, top_n=40):
    cnt = Counter()
    in_header = True
    with open(rinex_path, 'r') as f:
        for line in f:
            if in_header:
                if 'END OF HEADER' in line:
                    in_header = False
                continue
            if line and line[0] in 'GRECJ':
                sat = line[:3].strip()
                if len(sat) == 3:
                    cnt[sat] += 1
    return [sat for sat, _ in cnt.most_common(top_n)]


def run_exclusion(sat):
    out_rel = f'out\\solution_excl_{sat}.pos'
    cmd = [
        RTKLIB_EXE,
        '-p', '2',
        '-f', '1',
        '-sys', 'G,R,E,C,J',
        '-x', sat,
        '-o', out_rel,
    ] + BASE_FILES
    subprocess.run(cmd, cwd=WORKDIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return out_rel.replace('\\', '/')


def main():
    base = metrics('out/solution_first.pos')
    print('BASELINE', base)

    candidates = collect_candidates(RINEX, top_n=40)
    print('CANDIDATES', ', '.join(candidates))

    ranked = []
    for sat in candidates:
        out_path = run_exclusion(sat)
        if not os.path.exists(out_path):
            print('MISSING', sat)
            continue

        m = metrics(out_path)
        if not m:
            print('INVALID', sat)
            continue

        score = (
            (base['gt5'] - m['gt5']) * 100
            + (base['gt3'] - m['gt3']) * 10
            + (base['p95'] - m['p95']) * 5
            + (base['mean'] - m['mean'])
        )
        ranked.append((score, sat, out_path, m))
        print(f"DONE {sat} score={score:.2f} gt5={m['gt5']} gt3={m['gt3']} p95={m['p95']:.3f} mean={m['mean']:.3f}")

    ranked.sort(reverse=True, key=lambda x: x[0])
    print('\nTOP RESULTS:')
    for score, sat, out_path, m in ranked[:8]:
        print(f"{sat} -> score={score:.2f}, file={out_path}, gt5={m['gt5']}, gt3={m['gt3']}, p95={m['p95']:.3f}, mean={m['mean']:.3f}, max={m['max']:.3f}")

    if ranked:
        best = ranked[0]
        print('\nBEST_EXCLUSION', best[1])
        print('BEST_FILE', best[2])


if __name__ == '__main__':
    main()
