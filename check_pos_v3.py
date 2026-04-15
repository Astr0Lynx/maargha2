import math, os

def parse_pos(path, max_q=5):
    pts=[]; q_dist={}
    with open(path, 'r', errors='ignore') as f:
        for line in f:
            line=line.strip()
            if not line or line.startswith('%'): continue
            p=line.split()
            try:
                lat=float(p[2]); lon=float(p[3]); q=int(p[5])
                q_dist[q]=q_dist.get(q,0)+1
                if q<=max_q and 17<=lat<=19 and 77<=lon<=82:
                    pts.append((lat,lon))
            except: continue
    ql={1:'FIX',2:'FLOAT',3:'SBAS',4:'DGPS',5:'SINGLE',6:'PPP'}
    s='; '.join('Q{}({}): {}'.format(k,ql.get(k,'?'),v) for k,v in sorted(q_dist.items()))
    return pts, s

def hav(a,b):
    R=6371000; la1,lo1=math.radians(a[0]),math.radians(a[1]); la2,lo2=math.radians(b[0]),math.radians(b[1])
    x=math.sin((la2-la1)/2)**2+math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return R*2*math.asin(math.sqrt(min(1,x)))
def pdist(t): return sum(hav(t[i-1],t[i]) for i in range(1,len(t))) if len(t)>1 else 0
def ss(pts):
    if len(pts)<2: return 'no data'
    steps=sorted(hav(pts[i-1],pts[i]) for i in range(1,len(pts)))
    n=len(steps)
    return 'med={}m p90={}m max={}m'.format(round(steps[n//2],2),round(steps[int(.9*n)],2),round(steps[-1],2))

pts,qs=parse_pos('out/logger8_oneplus_dgps_v3.pos', max_q=4)
print('OnePlus DGPS v3: {} pts, {}m'.format(len(pts),round(pdist(pts))))
print('  Q:', qs)
print('  Steps:', ss(pts))

pts2,qs2=parse_pos('out/logger8_samsung_rtk_v3.pos', max_q=2)
print('Samsung RTK  v3: {} pts, {}m'.format(len(pts2),round(pdist(pts2))))
print('  Q:', qs2)
print('  Steps:', ss(pts2))
