#!/usr/bin/env python3
import hashlib
from pathlib import Path

p1 = Path('C:/Users/Guntesh/Desktop/foo/gsd/out/solution_first.pos')
p2 = Path('C:/Users/Guntesh/Desktop/foo/gsd/out/solution_excl_G06.pos')

b1 = p1.read_bytes()
b2 = p2.read_bytes()

print('size1', len(b1), 'size2', len(b2))
print('md5_1', hashlib.md5(b1).hexdigest())
print('md5_2', hashlib.md5(b2).hexdigest())
print('equal', b1 == b2)

print('\nheader baseline:')
print('\n'.join(p1.read_text(errors='ignore').splitlines()[:14]))
print('\nheader excl:')
print('\n'.join(p2.read_text(errors='ignore').splitlines()[:14]))
