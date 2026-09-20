"""Unregulated extraction in the same fixed cascade used by SMI-04."""
import math


def simulate(rain, et, capacity, initial, two=True):
    if len(rain)!=len(et) or capacity<=0 or not 0<=initial<=1:
        raise ValueError('invalid_inputs')
    caps=[capacity/3,2*capacity/3] if two else [capacity]
    stores=[c*initial for c in caps]
    out={k:[] for k in ('upper','lower','total','evaporation','transpiration','drainage')}
    error=0.
    for p,demand in zip(rain,et):
        if not (math.isfinite(p) and math.isfinite(demand) and p>=0 and demand>=0):
            raise ValueError('invalid_weather')
        before=sum(stores);incoming=p;evap=trans=0.
        for j,c in enumerate(caps):
            available=stores[j]+incoming
            incoming=max(0.,available-c)
            stores[j]=min(c,available)
        drainage=incoming
        for j,c in enumerate(caps):
            ep=demand*.5 if j==0 else 0.
            tp=demand*.5*c/capacity
            loss=min(stores[j],ep+tp)
            ratio=loss/(ep+tp) if ep+tp else 0.
            evap+=ep*ratio;trans+=tp*ratio;stores[j]-=loss
            assert 0<=stores[j]<=c
        error=max(error,abs(before+p-sum(stores)-evap-trans-drainage))
        for k,v in zip(out,(stores[0],stores[-1],sum(stores),evap,trans,drainage)):
            out[k].append(v)
    out['mass_error_max_mm']=max(error,abs(capacity*initial+sum(rain)-sum(stores)
        -sum(out['evaporation'])-sum(out['transpiration'])-sum(out['drainage'])))
    return out


def history(rain,et,capacity,two=True):
    caps=[capacity/3,2*capacity/3] if two else [capacity]
    out={k:[math.nan]*len(rain) for k in ('upper','lower','total')}
    start=0;errors=[]
    def finite(x):return isinstance(x,(int,float)) and math.isfinite(x)
    while start<len(rain):
        if not finite(rain[start]) or not finite(et[start]):start+=1;continue
        end=start
        while end<len(rain) and finite(rain[end]) and finite(et[end]):end+=1
        dry=simulate(rain[start:end],et[start:end],capacity,0.,two)
        wet=simulate(rain[start:end],et[start:end],capacity,1.,two)
        errors.extend([dry['mass_error_max_mm'],wet['mass_error_max_mm']])
        for i in range(end-start):
            keys=('upper','lower') if two else ('total',)
            assert all(dry[k][i]<=wet[k][i]+1e-9 for k in keys)
            if i+1>=90 and all(wet[k][i]-dry[k][i]<=max(.25,.01*c) for k,c in zip(keys,caps)):
                for k in out:out[k][start+i]=(dry[k][i]+wet[k][i])/2
        start=end
    out['mass_error_max_mm']=max(errors,default=0.)
    return out
