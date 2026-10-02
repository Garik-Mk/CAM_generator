import argparse, json, math
from pathlib import Path
import numpy as np
from PIL import Image


def parse_color(c):
    if isinstance(c, str):
        c = c.strip().lstrip('#')
        if len(c) != 6:
            raise ValueError(f'Invalid HEX color: {c}')
        return np.array([int(c[i:i+2], 16) for i in (0,2,4)], dtype=np.float32)
    return np.asarray(c, dtype=np.float32)


def periodic_noise(h, w, scale=100.0, aspect=1.0, angle=0.0, seed=0):
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((h, w))
    spec = np.fft.fft2(white)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    frx = c*fx + s*fy
    fry = -s*fx + c*fy
    aspect = max(0.01, aspect)
    sx, sy = scale*aspect, scale/aspect
    filt = np.exp(-2.0*math.pi**2*((frx*sx)**2 + (fry*sy)**2))
    f = np.fft.ifft2(spec*filt).real
    sd = f.std()
    return (f-f.mean())/sd if sd > 1e-12 else f-f.mean()


def fractal_periodic_noise(h, w, scale=100, aspect=1.0, angle=0.0, octaves=3, persistence=0.55, seed=0):
    out = np.zeros((h,w), dtype=np.float64)
    amp_sum = 0.0
    for o in range(octaves):
        amp = persistence**o
        out += amp*periodic_noise(h,w,max(1.5,scale/(2**o)),aspect,angle,seed+10007*o)
        amp_sum += amp
    out /= max(amp_sum, 1e-12)
    sd = out.std()
    return (out-out.mean())/sd if sd > 1e-12 else out-out.mean()


def threshold_mask(field, coverage=0.35, softness=0.0):
    coverage = float(np.clip(coverage, 0.0001, 0.9999))
    th = np.quantile(field, 1.0-coverage)
    if softness <= 0:
        return (field >= th).astype(np.float32)
    width = max(field.std()*softness, 1e-6)
    x = np.clip((field-th)/width, -30, 30)
    return (1.0/(1.0+np.exp(-x))).astype(np.float32)


def torus_delta(v, center, period):
    return ((v-center+period/2) % period) - period/2


def make_blob_mask(h,w,l):
    f = fractal_periodic_noise(h,w,l.get('scale',120),l.get('aspect',1.0),l.get('angle',0),l.get('octaves',3),l.get('persistence',0.55),l.get('seed',0))
    return threshold_mask(f,l.get('coverage',0.35),l.get('softness',0.0))


def make_digital_mask(h,w,l):
    bs = max(1,int(l.get('block_size',16)))
    cx, cy = max(2, round(w/bs)), max(2, round(h/bs))
    sc = max(1.2, l.get('scale',bs*5)/bs)
    small = fractal_periodic_noise(cy,cx,sc,l.get('aspect',1.0),l.get('angle',0),l.get('octaves',2),l.get('persistence',0.55),l.get('seed',0))
    xi = np.arange(w)*cx//w
    yi = np.arange(h)*cy//h
    f = small[yi[:,None], xi[None,:]]
    return threshold_mask(f,l.get('coverage',0.35),0)


def make_stripe_mask(h,w,l):
    yy,xx = np.mgrid[0:h,0:w]
    kx,ky = int(l.get('kx',2)), int(l.get('ky',6))
    phase = 2*math.pi*(kx*xx/w + ky*yy/h)
    warp = l.get('warp',2.5)
    if warp:
        d = fractal_periodic_noise(h,w,l.get('warp_scale',150),l.get('warp_aspect',1.0),l.get('warp_angle',0),l.get('octaves',3),l.get('persistence',0.55),l.get('seed',0))
        phase += d*warp
    return threshold_mask(np.sin(phase),l.get('coverage',0.30),l.get('softness',0.0))


def make_spot_mask(h,w,l):
    rng = np.random.default_rng(l.get('seed',0))
    count = int(l.get('count',30))
    rmin,rmax = l.get('min_radius',10),l.get('max_radius',50)
    amin,amax = l.get('min_aspect',0.5),l.get('max_aspect',2.0)
    yy,xx = np.mgrid[0:h,0:w]
    best = np.full((h,w), np.inf, dtype=np.float32)
    for _ in range(count):
        cx,cy = rng.uniform(0,w),rng.uniform(0,h)
        r = rng.uniform(rmin,rmax)
        asp = rng.uniform(amin,amax)
        rx,ry = r*asp, r/max(asp,0.01)
        a = rng.uniform(0,2*math.pi)
        dx,dy = torus_delta(xx,cx,w), torus_delta(yy,cy,h)
        c,s = math.cos(a),math.sin(a)
        xr,yr = c*dx+s*dy, -s*dx+c*dy
        d = (xr/rx)**2 + (yr/ry)**2
        best = np.minimum(best,d)
    irr = l.get('irregularity',0)
    if irr:
        best += fractal_periodic_noise(h,w,l.get('irregularity_scale',30),octaves=3,persistence=.55,seed=l.get('seed',0)+34567)*irr
    soft = l.get('softness',0)
    if soft <= 0:
        return (best <= 1).astype(np.float32)
    x = np.clip((1-best)/soft,-30,30)
    return (1/(1+np.exp(-x))).astype(np.float32)


def make_branch_mask(h,w,l):
    # thin branching/ridge-like forms from multi-scale periodic noise
    base = fractal_periodic_noise(h,w,l.get('scale',120),l.get('aspect',1.5),l.get('angle',0),l.get('octaves',4),l.get('persistence',0.55),l.get('seed',0))
    fine = fractal_periodic_noise(h,w,l.get('branch_scale',35),l.get('aspect',1.0),l.get('angle',0),3,0.5,l.get('seed',0)+911)
    ridge = -np.abs(base) + l.get('detail_strength',0.30)*fine
    return threshold_mask(ridge,l.get('coverage',0.16),l.get('softness',0.0))


def periodic_voronoi_distances(h,w,count,seed):
    rng=np.random.default_rng(seed)
    pts=np.column_stack([rng.uniform(0,w,count),rng.uniform(0,h,count)])
    yy,xx=np.mgrid[0:h,0:w]
    d1=np.full((h,w),np.inf,dtype=np.float32)
    d2=np.full((h,w),np.inf,dtype=np.float32)
    nearest=np.zeros((h,w),dtype=np.int32)
    for i,(cx,cy) in enumerate(pts):
        dx,dy=torus_delta(xx,cx,w),torus_delta(yy,cy,h)
        d=dx*dx+dy*dy
        better=d<d1
        d2=np.where(better,d1,np.minimum(d2,d))
        nearest=np.where(better,i,nearest)
        d1=np.where(better,d,d1)
    return d1,d2,nearest


def make_voronoi_mask(h,w,l):
    count=int(l.get('count',45))
    d1,d2,nearest=periodic_voronoi_distances(h,w,count,l.get('seed',0))
    mode=l.get('mode','cells')
    if mode=='edges':
        gap=np.sqrt(d2)-np.sqrt(d1)
        # small gap = close to cell border
        width=float(l.get('edge_width',8.0))
        return (gap <= width).astype(np.float32)
    # select a deterministic subset of cells
    rng=np.random.default_rng(l.get('seed',0)+999)
    selected=rng.random(count)<l.get('coverage',0.35)
    return selected[nearest].astype(np.float32)


def make_crack_mask(h,w,l):
    d1,d2,_=periodic_voronoi_distances(h,w,int(l.get('count',70)),l.get('seed',0))
    gap=np.sqrt(d2)-np.sqrt(d1)
    width=float(l.get('width',2.5))
    mask=(gap <= width).astype(np.float32)
    rough=l.get('roughness',0.0)
    if rough:
        noise=fractal_periodic_noise(h,w,l.get('rough_scale',25),octaves=3,persistence=.55,seed=l.get('seed',0)+321)
        mask=((gap + noise*rough) <= width).astype(np.float32)
    return mask


def make_leaf_mask(h,w,l):
    rng=np.random.default_rng(l.get('seed',0))
    count=int(l.get('count',30))
    yy,xx=np.mgrid[0:h,0:w]
    out=np.zeros((h,w),dtype=np.float32)
    for _ in range(count):
        cx,cy=rng.uniform(0,w),rng.uniform(0,h)
        length=rng.uniform(l.get('min_length',35),l.get('max_length',90))
        width=rng.uniform(l.get('min_width',10),l.get('max_width',28))
        a=rng.uniform(0,2*math.pi)
        dx,dy=torus_delta(xx,cx,w),torus_delta(yy,cy,h)
        c,s=math.cos(a),math.sin(a)
        xr,yr=c*dx+s*dy,-s*dx+c*dy
        # pointed leaf: ellipse narrowed linearly towards ends
        xn=np.abs(xr)/(length/2)
        half_w=(width/2)*np.clip(1-xn,0,1)**l.get('pointiness',0.65)
        leaf=(xn<=1) & (np.abs(yr)<=half_w)
        out=np.maximum(out,leaf.astype(np.float32))
        if l.get('veins',False):
            vein=(xn<=.85) & (np.abs(yr)<=max(1.0,l.get('vein_width',1.5)))
            out=np.maximum(out,vein.astype(np.float32))
    return out


def make_brush_mask(h,w,l):
    rng=np.random.default_rng(l.get('seed',0))
    strokes=int(l.get('count',24))
    yy,xx=np.mgrid[0:h,0:w]
    field=np.zeros((h,w),dtype=np.float32)
    for _ in range(strokes):
        cx,cy=rng.uniform(0,w),rng.uniform(0,h)
        length=rng.uniform(l.get('min_length',70),l.get('max_length',220))
        width=rng.uniform(l.get('min_width',8),l.get('max_width',30))
        a=math.radians(l.get('angle',0)+rng.uniform(-l.get('angle_jitter',35),l.get('angle_jitter',35)))
        dx,dy=torus_delta(xx,cx,w),torus_delta(yy,cy,h)
        c,s=math.cos(a),math.sin(a)
        xr,yr=c*dx+s*dy,-s*dx+c*dy
        # capsule / brush stroke
        core=np.clip(np.abs(xr)-length/2,0,None)
        dist=np.sqrt(core*core+yr*yr)
        stroke=(dist <= width/2).astype(np.float32)
        field=np.maximum(field,stroke)
    rough=l.get('roughness',0.0)
    if rough:
        n=fractal_periodic_noise(h,w,l.get('rough_scale',18),octaves=3,persistence=.5,seed=l.get('seed',0)+777)
        field=np.where(n > -rough, field, 0)
    return field.astype(np.float32)



def make_clustered_spot_mask(h,w,l):
    """Clusters of small organic spots, useful for Flecktarn-like dot groups.

    All distances are toroidal, so clusters that cross an edge continue on the
    opposite edge.  A spot may have several overlapping lobes to avoid the
    perfectly elliptical look of the basic ``spots`` layer.
    """
    rng=np.random.default_rng(l.get('seed',0))
    count=max(1,int(l.get('count',60)))
    groups=max(1,int(l.get('groups',max(2,round(count/10)))))
    spread=float(l.get('spread',45.0))
    rmin=float(l.get('min_radius',4.0))
    rmax=float(l.get('max_radius',14.0))
    amin=float(l.get('min_aspect',0.65))
    amax=float(l.get('max_aspect',1.55))
    lmin=max(1,int(l.get('min_lobes',1)))
    lmax=max(lmin,int(l.get('max_lobes',3)))
    lobe_offset=float(l.get('lobe_offset',0.55))
    yy,xx=np.mgrid[0:h,0:w]
    out=np.zeros((h,w),dtype=np.float32)
    centers=np.column_stack([rng.uniform(0,w,groups),rng.uniform(0,h,groups)])
    for i in range(count):
        gx,gy=centers[i % groups]
        cx=(gx+rng.normal(0,spread))%w
        cy=(gy+rng.normal(0,spread))%h
        base_r=rng.uniform(rmin,rmax)
        lobes=int(rng.integers(lmin,lmax+1))
        for _ in range(lobes):
            a=rng.uniform(0,2*math.pi)
            off=rng.uniform(0,base_r*lobe_offset)
            lx=(cx+math.cos(a)*off)%w
            ly=(cy+math.sin(a)*off)%h
            r=base_r*rng.uniform(.72,1.08)
            asp=rng.uniform(amin,amax)
            rx,ry=r*asp,r/max(asp,.01)
            ang=rng.uniform(0,2*math.pi)
            dx,dy=torus_delta(xx,lx,w),torus_delta(yy,ly,h)
            c,s=math.cos(ang),math.sin(ang)
            xr,yr=c*dx+s*dy,-s*dx+c*dy
            d=(xr/rx)**2+(yr/ry)**2
            out=np.maximum(out,(d<=1).astype(np.float32))
    rough=float(l.get('roughness',0.0))
    if rough>0:
        n=fractal_periodic_noise(h,w,l.get('rough_scale',18),octaves=3,persistence=.5,seed=l.get('seed',0)+8123)
        out=np.where(n>-rough,out,0).astype(np.float32)
    return out


def make_multicolor_blob_image(h,w,l):
    """Generate an interlocking multi-colour organic field.

    Instead of overlaying independent binary blob layers, each pixel is owned
    by exactly one colour.  This is much better for patterns such as Flecktarn,
    where several colours form interlocking macro-regions.
    """
    colors=l.get('colors')
    if not colors or len(colors)<2:
        raise ValueError('multicolor_blobs needs at least two colors')
    n=len(colors)
    cov=np.asarray(l.get('coverages',[1.0/n]*n),dtype=float)
    if len(cov)!=n:
        raise ValueError('coverages must have same length as colors')
    cov=np.clip(cov,1e-4,None)
    cov=cov/cov.sum()
    scales=l.get('scales')
    if scales is None:
        scales=[float(l.get('scale',120))]*n
    elif len(scales)!=n:
        raise ValueError('scales must have same length as colors')
    aspects=l.get('aspects',[l.get('aspect',1.0)]*n)
    angles=l.get('angles',[l.get('angle',0.0)]*n)
    octaves=int(l.get('octaves',4))
    persistence=float(l.get('persistence',0.55))
    seed=int(l.get('seed',0))
    fields=[]
    for i in range(n):
        f=fractal_periodic_noise(h,w,float(scales[i]),float(aspects[i]),float(angles[i]),octaves,persistence,seed+1009*i)
        fields.append(f)
    fields=np.stack(fields,axis=0)
    bias=np.zeros(n,dtype=np.float64)
    # Iteratively adjust the per-colour bias so the actual area fractions are
    # close to the requested coverages.
    for _ in range(int(l.get('coverage_iterations',70))):
        lab=np.argmax(fields+bias[:,None,None],axis=0)
        cur=np.bincount(lab.ravel(),minlength=n)/lab.size
        err=np.log(cov/np.clip(cur,1e-6,None))
        bias+=float(l.get('coverage_lr',0.35))*err
        bias-=bias.mean()
        if np.max(np.abs(cur-cov))<0.003:
            break
    lab=np.argmax(fields+bias[:,None,None],axis=0)
    palette=np.stack([parse_color(c) for c in colors],axis=0)
    return palette[lab].astype(np.float32)


def create_layer_mask(h,w,l):
    t=l.get('type','blobs').lower()
    if t in {'blob','blobs','organic'}: return make_blob_mask(h,w,l)
    if t in {'digital','pixel','pixels'}: return make_digital_mask(h,w,l)
    if t in {'microdigital','micro-digital','micro_digital'}:
        l=dict(l); l.setdefault('block_size',4); l.setdefault('scale',26); l.setdefault('octaves',2)
        return make_digital_mask(h,w,l)
    if t in {'stripe','stripes','tiger'}: return make_stripe_mask(h,w,l)
    if t in {'spot','spots','ellipse','ellipses'}: return make_spot_mask(h,w,l)
    if t in {'clustered_spots','clustered-spots','fleck','flecks','amoeba_spots','amoeba-spots'}: return make_clustered_spot_mask(h,w,l)
    if t in {'branch','branches'}: return make_branch_mask(h,w,l)
    if t in {'voronoi'}: return make_voronoi_mask(h,w,l)
    if t in {'crack','cracks','network'}: return make_crack_mask(h,w,l)
    if t in {'leaf','leaves'}: return make_leaf_mask(h,w,l)
    if t in {'brush','brushstroke','brush-stroke'}: return make_brush_mask(h,w,l)
    raise ValueError(f'Unknown layer type: {t}')


def generate_camouflage(cfg):
    w,h=int(cfg.get('width',1024)),int(cfg.get('height',1024))
    img=np.zeros((h,w,3),dtype=np.float32)
    img[:]=parse_color(cfg.get('base_color','#6B7045'))
    layers=cfg.get('layers',[])
    for i,l in enumerate(layers,1):
        t=l.get('type','blobs').lower()
        print(f'Layer {i}/{len(layers)}: {t}')
        if t in {'multicolor_blobs','multicolor-blobs','palette_blobs','palette-blobs'}:
            layer_img=make_multicolor_blob_image(h,w,l)
            opacity=float(l.get('opacity',1.0))
            img=img*(1-opacity)+layer_img*opacity
            continue
        m=create_layer_mask(h,w,l)
        opacity=float(l.get('opacity',1.0))
        m=np.clip(m*opacity,0,1)
        c=parse_color(l['color'])
        img=img*(1-m[...,None])+c*m[...,None]
    return np.clip(img,0,255).astype(np.uint8)


PRESETS={
 'woodland':{
  'width':1024,'height':1024,'base_color':'#8A8451',
  'layers':[
   {'type':'blobs','color':'#46563B','coverage':.47,'scale':170,'octaves':4,'seed':10},
   {'type':'blobs','color':'#5C442C','coverage':.26,'scale':105,'aspect':1.4,'angle':30,'octaves':3,'seed':20},
   {'type':'blobs','color':'#20261E','coverage':.15,'scale':65,'aspect':1.7,'angle':-25,'octaves':3,'seed':30},
  ]},
 'digital':{
  'width':1024,'height':1024,'base_color':'#8F9877',
  'layers':[
   {'type':'digital','color':'#58634B','coverage':.48,'block_size':14,'scale':95,'seed':100},
   {'type':'digital','color':'#343D32','coverage':.27,'block_size':10,'scale':55,'seed':200},
   {'type':'microdigital','color':'#B0AA88','coverage':.13,'block_size':4,'scale':26,'seed':300},
  ]},
 'flecktarn':{
  'width':1024,'height':1024,'base_color':'#7F7A52',
  'layers':[
   {'type':'blobs','color':'#4B5434','coverage':.48,'scale':125,'octaves':4,'persistence':.52,'seed':101},
   {'type':'spots','color':'#2E3A27','count':95,'min_radius':6,'max_radius':24,'min_aspect':.55,'max_aspect':1.7,'irregularity':.14,'irregularity_scale':12,'seed':102},
   {'type':'spots','color':'#6B4935','count':78,'min_radius':5,'max_radius':20,'min_aspect':.6,'max_aspect':1.6,'irregularity':.16,'irregularity_scale':10,'seed':103},
   {'type':'spots','color':'#1C211A','count':70,'min_radius':3,'max_radius':13,'min_aspect':.7,'max_aspect':1.5,'seed':104},
   {'type':'spots','color':'#A39A72','count':42,'min_radius':4,'max_radius':11,'min_aspect':.8,'max_aspect':1.4,'seed':105},
  ]},
 'splittertarn':{
  'width':1024,'height':1024,'base_color':'#A49D73',
  'layers':[
   {'type':'voronoi','mode':'cells','color':'#69704B','count':34,'coverage':.42,'seed':410},
   {'type':'voronoi','mode':'cells','color':'#79563D','count':30,'coverage':.24,'seed':420},
   {'type':'brush','color':'#4D573C','count':150,'min_length':18,'max_length':42,'min_width':2,'max_width':4,'angle':62,'angle_jitter':7,'seed':430},
  ]},
 'tiger':{
  'width':1024,'height':1024,'base_color':'#69724E',
  'layers':[
   {'type':'stripes','color':'#263225','kx':2,'ky':8,'coverage':.30,'warp':3.1,'warp_scale':100,'seed':501},
   {'type':'stripes','color':'#393A29','kx':2,'ky':6,'coverage':.16,'warp':4,'warp_scale':70,'seed':502},
  ]}
}


def save_image(arr,filename):
    Image.fromarray(arr,'RGB').save(filename)


def save_tile_preview(img,filename,repetitions=3):
    save_image(np.tile(img,(repetitions,repetitions,1)),filename)


def main():
    p=argparse.ArgumentParser(description='Procedural seamless camouflage generator')
    p.add_argument('--preset',choices=PRESETS.keys(),default='woodland')
    p.add_argument('--config',type=str)
    p.add_argument('--output',default='camouflage.png')
    p.add_argument('--preview',action='store_true')
    a=p.parse_args()
    if a.config:
        with open(a.config,'r',encoding='utf-8') as f: cfg=json.load(f)
    else:
        cfg=json.loads(json.dumps(PRESETS[a.preset]))
    img=generate_camouflage(cfg)
    save_image(img,a.output)
    print('Saved:',a.output)
    if a.preview:
        out=Path(a.output)
        prev=out.parent/(out.stem+'_preview.png')
        save_tile_preview(img,prev)
        print('Saved preview:',prev)

if __name__=='__main__':
    main()
