#!/usr/bin/env python3
"""Analyze a camouflage reference image and create a procedural config.

The fitter is intentionally statistical: it estimates palette, area fractions,
macro-region scale and micro-spot structure.  It does not copy the source image
or reconstruct its exact geometry.

Best results: organic / Flecktarn / woodland-like patterns.
Digital and stripe families are detected and fitted more approximately.
"""

import argparse
import importlib.util
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


def rgb_hex(v):
    v=np.clip(np.rint(v),0,255).astype(int)
    return '#%02X%02X%02X' % tuple(v.tolist())


def load_rgb(path, max_analysis=720):
    im=Image.open(path).convert('RGB')
    arr=np.array(im)
    h,w=arr.shape[:2]
    scale=min(1.0, float(max_analysis)/max(h,w))
    if scale < 1:
        arr=cv2.resize(arr,(max(2,round(w*scale)),max(2,round(h*scale))),interpolation=cv2.INTER_AREA)
    return arr, im.size


def kmeans_once(sample, k, attempts=5):
    criteria=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,60,0.15)
    compact,labels,centers=cv2.kmeans(sample.astype(np.float32),k,None,criteria,attempts,cv2.KMEANS_PP_CENTERS)
    return compact/len(sample), centers


def choose_k(lab, kmin=3, kmax=7):
    flat=lab.reshape(-1,3)
    step=max(1,len(flat)//45000)
    sample=flat[::step].astype(np.float32)
    errors=[]
    centers=[]
    for k in range(kmin,kmax+1):
        e,c=kmeans_once(sample,k,attempts=4)
        errors.append(e); centers.append(c)
    # Elbow: stop before the first extra colour whose relative benefit is small.
    # 0.22 was deliberately chosen conservatively for textured fabric photos.
    improvements=[1-errors[i]/errors[i-1] for i in range(1,len(errors))]
    chosen=kmax
    for i,imp in enumerate(improvements, start=1):
        k=kmin+i
        if k>=4 and imp < 0.22:
            chosen=k-1
            break
    idx=chosen-kmin
    return chosen, centers[idx], errors, improvements


def quantize(arr, colors='auto', blur_sigma=None):
    h,w=arr.shape[:2]
    if blur_sigma is None:
        blur_sigma=max(0.8,min(h,w)/500.0)
    smooth=cv2.GaussianBlur(arr,(0,0),blur_sigma)
    lab=cv2.cvtColor(smooth,cv2.COLOR_RGB2LAB)
    if colors == 'auto':
        k,centers,errors,improvements=choose_k(lab)
    else:
        k=int(colors)
        flat=lab.reshape(-1,3)
        step=max(1,len(flat)//50000)
        _,centers=kmeans_once(flat[::step],k,attempts=8)
        errors=[]; improvements=[]
    flat=lab.reshape(-1,3).astype(np.float32)
    # assign all pixels to nearest Lab centre
    labels=np.argmin(((flat[:,None,:]-centers[None,:,:])**2).sum(axis=2),axis=1).reshape(h,w).astype(np.uint8)
    # suppress fabric weave / JPEG chatter without destroying the camouflage edge
    labels=cv2.medianBlur(labels,5 if min(h,w)>=350 else 3)
    palette=[]; coverage=[]
    for i in range(k):
        pix=arr[labels==i]
        if len(pix):
            palette.append(np.median(pix,axis=0))
        else:
            palette.append(np.array([0,0,0]))
        coverage.append(float(np.mean(labels==i)))
    return labels,np.asarray(palette),np.asarray(coverage),{
        'k':k,'blur_sigma':blur_sigma,'kmeans_errors':errors,'kmeans_improvements':improvements
    }


def boundary_run_lengths(a, axis):
    if axis==1:
        a=a.T
    lens=[]
    for col in a.T:
        x=np.r_[False,col,False].astype(np.int8)
        d=np.diff(x)
        starts=np.where(d==1)[0]; ends=np.where(d==-1)[0]
        lens.extend((ends-starts).tolist())
    return np.asarray(lens,dtype=float)


def style_scores(arr, labels):
    # Digital score: percentage of quantized boundary length contained in long
    # exact horizontal/vertical runs.
    v=labels[:,1:]!=labels[:,:-1]
    h=labels[1:,:]!=labels[:-1,:]
    lv=boundary_run_lengths(v,0)
    lh=boundary_run_lengths(h,1)
    runs=np.r_[lv,lh]
    run_thr=max(4,min(labels.shape)//100)
    digital=float(runs[runs>=run_thr].sum()/max(1.0,runs.sum())) if len(runs) else 0.0

    # Stripe score: coherence of edge orientation.
    gray=cv2.cvtColor(arr,cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray=cv2.GaussianBlur(gray,(0,0),max(1.0,min(arr.shape[:2])/300.0))
    gx=cv2.Sobel(gray,cv2.CV_32F,1,0,ksize=3)
    gy=cv2.Sobel(gray,cv2.CV_32F,0,1,ksize=3)
    mag=np.hypot(gx,gy)
    mask=mag>np.quantile(mag,.75)
    if np.any(mask):
        theta=np.arctan2(gy[mask],gx[mask])
        weights=mag[mask]
        z=np.sum(weights*np.exp(2j*theta))
        stripe=float(abs(z)/max(1e-9,weights.sum()))
        normal_angle=float(np.degrees(.5*np.angle(z)))
    else:
        stripe=0.0; normal_angle=0.0
    return {'digital':digital,'stripe':stripe,'normal_angle':normal_angle}


def periodic_nn_dist(points, w, h):
    if len(points)<2:
        return np.array([])
    p=np.asarray(points,float)
    out=[]
    for i in range(len(p)):
        dx=np.abs(p[:,0]-p[i,0]); dx=np.minimum(dx,w-dx)
        dy=np.abs(p[:,1]-p[i,1]); dy=np.minimum(dy,h-dy)
        d=np.hypot(dx,dy); d[i]=np.inf
        out.append(d.min())
    return np.asarray(out)


def component_stats(mask, image_area, min_dim):
    n,lab,stats,cents=cv2.connectedComponentsWithStats(mask.astype(np.uint8),8)
    if n<=1:
        return {'all':[], 'macro':[], 'micro':[], 'centroids':[]}
    comps=[]
    big_threshold=max(40,int(image_area*0.004))
    tiny_threshold=max(6,int(image_area*0.00004))
    for i in range(1,n):
        area=int(stats[i,cv2.CC_STAT_AREA])
        if area<tiny_threshold:
            continue
        x,y=cents[i]
        diam=math.sqrt(4*area/math.pi)
        comps.append({'area':area,'diameter':diam,'centroid':(float(x),float(y))})
    macro=[c for c in comps if c['area']>=big_threshold]
    micro=[c for c in comps if c['area']<big_threshold]
    return {'all':comps,'macro':macro,'micro':micro,'centroids':[c['centroid'] for c in micro]}


def organic_config(arr, labels, palette, coverage, original_size, seed=1000):
    h,w=labels.shape
    min_dim=min(h,w)
    area=h*w
    stats=[]
    macro_area=[]
    macro_scales=[]
    for i in range(len(palette)):
        s=component_stats(labels==i,area,min_dim)
        stats.append(s)
        ma=sum(c['area'] for c in s['macro'])/area
        macro_area.append(ma)
        if s['macro']:
            di=np.asarray([c['diameter'] for c in s['macro']])
            # empirically maps connected-region diameter to the generator's
            # low-frequency Gaussian scale reasonably well.
            sc=float(np.clip(np.quantile(di,.65)*0.35, min_dim*.035, min_dim*.20))
        else:
            sc=float(min_dim*.10)
        macro_scales.append(sc)

    macro=np.asarray(macro_area,float)
    # If segmentation does not produce enough big components, fall back to the
    # total colour coverage.  Otherwise normalise macro ownership to one full
    # interlocking field.
    if macro.sum()<0.40:
        macro=coverage.copy()
    macro=np.clip(macro,0.01,None); macro/=macro.sum()

    # Keep image dimensions equal to the reference.  Parameters are expressed
    # in pixels, so this preserves the measured feature scale.
    ow,oh=original_size
    sx=ow/w; sy=oh/h; size_scale=(sx+sy)/2
    pal=[rgb_hex(c) for c in palette]
    layers=[{
        'type':'multicolor_blobs',
        'colors':pal,
        'coverages':[round(float(x),5) for x in macro],
        'scales':[round(float(x*size_scale),2) for x in macro_scales],
        'octaves':4,
        'persistence':0.54,
        'seed':int(seed)
    }]

    report=[]
    for i,s in enumerate(stats):
        micro=s['micro']
        micro_area=sum(c['area'] for c in micro)/area
        macro_part=sum(c['area'] for c in s['macro'])/area
        entry={
            'color':pal[i],
            'coverage':float(coverage[i]),
            'macro_area':float(macro_part),
            'micro_area':float(micro_area),
            'macro_components':len(s['macro']),
            'micro_components':len(micro)
        }
        if micro:
            diam=np.asarray([c['diameter'] for c in micro])
            # Ignore the tiniest residue after segmentation when estimating dots.
            useful=diam[diam>=max(2.5,min_dim*.006)]
            if len(useful)==0: useful=diam
            rmin=float(np.clip(np.quantile(useful,.20)/2,2.0,min_dim*.035))*size_scale
            rmax=float(np.clip(np.quantile(useful,.80)/2,3.0,min_dim*.070))*size_scale
            count=int(np.clip(round(len(useful)*size_scale*size_scale),3,260))
            nn=periodic_nn_dist(s['centroids'],w,h)
            if len(nn):
                spread=float(np.clip(np.quantile(nn,.65)*1.6,min_dim*.025,min_dim*.13))*size_scale
            else:
                spread=min_dim*.06*size_scale
            groups=max(2,int(round(math.sqrt(count)*0.9)))
            entry.update({'spot_radius':[rmin,rmax],'spot_count':count,'spot_groups':groups,'spot_spread':spread})
            # Only add a micro layer when it occupies a meaningful part of the
            # picture. This prevents noise from becoming fake dots.
            if micro_area>=0.006 and count>=4:
                layers.append({
                    'type':'clustered_spots',
                    'color':pal[i],
                    'count':count,
                    'groups':groups,
                    'spread':round(spread,2),
                    'min_radius':round(rmin,2),
                    'max_radius':round(max(rmin+1,rmax),2),
                    'min_aspect':0.62,
                    'max_aspect':1.55,
                    'min_lobes':1,
                    'max_lobes':3,
                    'lobe_offset':0.50,
                    'seed':int(seed+101*(i+1))
                })
        report.append(entry)

    cfg={
        'width':int(ow),'height':int(oh),
        'base_color':pal[int(np.argmax(coverage))],
        'layers':layers
    }
    return cfg,report


def digital_config(arr,labels,palette,coverage,original_size,seed=2000):
    ow,oh=original_size; h,w=labels.shape; scale=(ow/w+oh/h)/2
    order=np.argsort(-coverage)
    base=int(order[0])
    # Estimate a conservative pixel block from median straight boundary run.
    v=labels[:,1:]!=labels[:,:-1]; hh=labels[1:,:]!=labels[:-1,:]
    runs=np.r_[boundary_run_lengths(v,0),boundary_run_lengths(hh,1)]
    runs=runs[runs>=2]
    bs=int(round((np.median(runs) if len(runs) else max(3,min(h,w)/80))*scale))
    bs=max(2,bs)
    layers=[]
    remaining=1.0
    # largest class becomes the base; later layers are approximate because
    # independent masks can overwrite each other.
    for rank,i in enumerate(order[1:],1):
        c=float(np.clip(coverage[i]/max(remaining,1e-5),.01,.85))
        remaining*=1-c
        layers.append({'type':'digital','color':rgb_hex(palette[i]),'coverage':round(c,5),
                       'block_size':bs,'scale':round(bs*(5.0+rank),2),'octaves':2,'seed':seed+rank*97})
    return {'width':ow,'height':oh,'base_color':rgb_hex(palette[base]),'layers':layers}, {'block_size':bs}


def stripe_config(arr,labels,palette,coverage,original_size,angle_normal,seed=3000):
    ow,oh=original_size
    order=np.argsort(-coverage); base=int(order[0])
    # kx/ky determine the stripe normal. Pick a small integer pair close to the
    # measured normal direction.
    a=math.radians(angle_normal)
    vx,vy=math.cos(a),math.sin(a)
    best=(1,5,1e9)
    for kx in range(-8,9):
        for ky in range(-8,9):
            if kx==0 and ky==0: continue
            n=math.hypot(kx/max(1,ow),ky/max(1,oh))
            ux=(kx/max(1,ow))/n; uy=(ky/max(1,oh))/n
            err=min((ux-vx)**2+(uy-vy)**2,(ux+vx)**2+(uy+vy)**2)
            if err<best[2]: best=(kx,ky,err)
    kx,ky=best[:2]
    layers=[]; remaining=1.0
    for rank,i in enumerate(order[1:],1):
        c=float(np.clip(coverage[i]/max(remaining,1e-5),.01,.75)); remaining*=1-c
        layers.append({'type':'stripes','color':rgb_hex(palette[i]),'kx':int(kx),'ky':int(ky),
                       'coverage':round(c,5),'warp':2.6+0.35*rank,'warp_scale':round(min(ow,oh)*.12,2),
                       'seed':seed+rank*113})
    return {'width':ow,'height':oh,'base_color':rgb_hex(palette[base]),'layers':layers}, {'kx':kx,'ky':ky}


def import_generator(path):
    spec=importlib.util.spec_from_file_location('camo_generator_dynamic',path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def main():
    ap=argparse.ArgumentParser(description='Fit a procedural camouflage config to a reference image')
    ap.add_argument('reference')
    ap.add_argument('--output','-o',default='fitted_camouflage.json')
    ap.add_argument('--colors',default='auto',help='palette size (3..8) or auto')
    ap.add_argument('--style',choices=['auto','organic','digital','stripes'],default='auto')
    ap.add_argument('--seed',type=int,default=1000)
    ap.add_argument('--report',default=None,help='optional analysis report JSON')
    ap.add_argument('--preview',default=None,help='optional generated preview PNG')
    ap.add_argument('--generator',default=str(Path(__file__).with_name('camouflage_generator_v3.py')))
    ap.add_argument('--max-analysis',type=int,default=720)
    args=ap.parse_args()

    arr,original_size=load_rgb(args.reference,args.max_analysis)
    colors=args.colors if args.colors=='auto' else int(args.colors)
    labels,palette,coverage,qinfo=quantize(arr,colors)
    scores=style_scores(arr,labels)

    if args.style=='auto':
        # These thresholds are intentionally conservative; ambiguous images are
        # treated as organic rather than forcing a wrong digital/stripe model.
        if scores['stripe']>0.46:
            style='stripes'
        elif scores['digital']>0.34:
            style='digital'
        else:
            style='organic'
    else:
        style=args.style

    if style=='organic':
        cfg,detail=organic_config(arr,labels,palette,coverage,original_size,args.seed)
    elif style=='digital':
        cfg,detail=digital_config(arr,labels,palette,coverage,original_size,args.seed)
    else:
        cfg,detail=stripe_config(arr,labels,palette,coverage,original_size,scores['normal_angle'],args.seed)

    Path(args.output).write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8')

    report={
        'reference':str(args.reference),
        'original_size':list(original_size),
        'analysis_size':[arr.shape[1],arr.shape[0]],
        'selected_style':style,
        'style_scores':scores,
        'palette_colors':[rgb_hex(c) for c in palette],
        'palette_coverages':[float(x) for x in coverage],
        'quantization':qinfo,
        'detail':detail
    }
    report_path=args.report or str(Path(args.output).with_suffix('.analysis.json'))
    Path(report_path).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

    print('Style:',style)
    print('Palette:')
    for c,a in sorted(zip(report['palette_colors'],coverage),key=lambda x:-x[1]):
        print(f'  {c}: {a*100:.1f}%')
    print('Saved config:',args.output)
    print('Saved analysis:',report_path)

    if args.preview:
        gen=import_generator(args.generator)
        img=gen.generate_camouflage(cfg)
        Image.fromarray(img,'RGB').save(args.preview)
        print('Saved preview:',args.preview)


if __name__=='__main__':
    main()
