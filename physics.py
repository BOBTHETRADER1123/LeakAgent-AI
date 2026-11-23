"""SI hydraulic formulas, and a small weighted cycle-model comparison."""
import math

RHO=1000.0
G=9.81


def head(p_kpa, velocity, elevation):
    return p_kpa*1000/(RHO*G)+velocity**2/(2*G)+elevation


def velocity(q_l_s, diameter_m):
    return q_l_s/1000/(math.pi*diameter_m**2/4)


def friction(length_m, diameter_m, v, factor=0.02):
    return factor*length_m/diameter_m*v**2/(2*G)


def orifice(pressure_kpa, diameter_m, cd=0.62):
    return cd*math.pi*diameter_m**2/4*math.sqrt(2*pressure_kpa*1000/RHO)*1000


def residual(r):
    value=r.q_up_l_s-r.q_down_l_s-r.pipe_storage_change_l_s-r.branch_tap_l_s
    sigma=math.hypot(r.meter_up_sigma_l_s,r.meter_down_sigma_l_s)
    return value,sigma


def fit_models(rows):
    # Exactly one pre-aggregated stable window per cycle. Known independent random meter sigma assumed.
    stable=[r for r in rows if r.full_pipe_flag and r.stable_window_verified]
    if len(stable)<4 or len({r.cycle_id for r in stable})!=len(stable):
        return {'status':'insufficient distinct stable windows'}
    p=[(r.p_up_kpa+r.p_down_kpa)/2 for r in stable]
    q=[r.q_up_l_s for r in stable]
    y,s=zip(*(residual(r) for r in stable))
    if min(p)<=0 or max(p)/min(p)<1.5:
        return {'status':'insufficient pressure spread'}
    w=[1/v**2 for v in s]
    def fit(x, k, positive=False):
        denom=sum(a*b*b for a,b in zip(w,x))
        c=sum(a*b*d for a,b,d in zip(w,x,y))/denom if denom else 0
        if positive: c=max(0,c)
        loss=sum(a*(d-c*b)**2 for a,b,d in zip(w,x,y))
        return {'coefficient':c,'bic':loss+k*math.log(len(y))}
    models={'normal':{'bic':sum(a*b*b for a,b in zip(w,y))},'offset':fit([1]*len(y),1),'scale':fit(q,1)}
    options=[]
    for i in range(41):
        n=0.5+i*0.05
        result=fit([(v/100)**n for v in p],2,True)
        options.append({**result,'exponent':round(n,2)})
    models['leak']=min(options,key=lambda m:m['bic'])
    ranking=sorted(models,key=lambda k:models[k]['bic'])
    gap=models[ranking[1]]['bic']-models[ranking[0]]['bic']
    # Fit at alternative endpoint pressures to test sensitivity; not statistical confidence intervals.
    return {'status':'tentative' if gap>=2 else 'ambiguous','leading':ranking[0], 'bic_gap':gap,'models':models,'pressure_proxy_kpa':p,'pressure_endpoints_kpa':[[r.p_up_kpa,r.p_down_kpa] for r in stable], 'note':'Leak coefficient is L/s at 100 kPa. Midpoint pressure is a proxy, not measured leak pressure. Requires independent verification; BIC assumes independent Gaussian random errors.'}
