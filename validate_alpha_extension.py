"""Validate the alpha-fair theoretical extension without changing the benchmark."""
from pathlib import Path
import json
import numpy as np
from scipy.optimize import minimize_scalar


def utility(x,w,xi,alpha):
    y=x+xi
    if alpha==1:
        return float(w@np.log(y))
    return float(w@np.expm1((1-alpha)*np.log(y))/(1-alpha))


def ray_scale(q,w,xi,gamma,alpha):
    a=(w/q)**(1/alpha)
    g=q*a
    beta=xi/a
    order=np.argsort(beta)
    beta=beta[order]
    G=np.cumsum(g[order])
    H=np.cumsum((q*xi)[order])
    cuts=beta*np.r_[0.,G[:-1]]-np.r_[0.,H[:-1]]
    k=int(np.searchsorted(np.maximum.accumulate(cuts),gamma,side='right'))
    k=max(1,min(len(w),k))
    b=(gamma+H[k-1])/G[k-1]
    return b**(-alpha)


def dual_on_ray(t,q,w,xi,gamma,alpha):
    x=np.maximum(0,(w/(t*q))**(1/alpha)-xi)
    return utility(x,w,xi,alpha)-float(t*q@x)+t*gamma


def main():
    rng=np.random.default_rng(31017)
    largest_relative_ray_error=0.
    largest_equality_error=0.
    largest_variance_violation=0.
    ray_cases=0;sharpness=[]
    for alpha in [.2,.5,1.,2.,4.]:
        for _ in range(30):
            w=np.exp(rng.normal(0,.3,37))
            q=np.exp(rng.normal(0,.2,37))
            xi=rng.uniform(0,1,37)
            gamma=float(rng.uniform(5,40))
            t=ray_scale(q,w,xi,gamma,alpha)
            check=minimize_scalar(lambda ell:dual_on_ray(np.exp(ell),q,w,xi,gamma,alpha),
                                  bounds=(np.log(t)-3,np.log(t)+3),method='bounded',
                                  options={'xatol':1e-12})
            actual=dual_on_ray(t,q,w,xi,gamma,alpha)
            error=abs(actual-check.fun)/max(1,abs(actual))
            largest_relative_ray_error=max(largest_relative_ray_error,error)
            assert error<1e-9
            ray_cases+=1
        for d in [2,5,40]:
            y0=rng.uniform(.7,1.3,d)
            theta=rng.uniform(.05,.35,d)
            w=y0**alpha
            xi=y0*theta
            x0=y0-xi
            p=y0/y0.sum()
            c=x0.sum()
            for s in [.6,.8,.95]:
                z=s+(1-s)*theta
                mean=float(p@z)
                assert theta.max()<mean
                optimum=y0*mean-xi
                actual=(utility(optimum,w,xi,alpha)-utility(s*x0,w,xi,alpha))/y0.sum()
                if alpha==1:
                    bound=np.log(mean)-float(p@np.log(z))
                else:
                    power=1-alpha
                    # Stable evaluation uses expm1 to cancel allocation constants.
                    bound=(np.expm1(power*np.log(mean))-float(p@np.expm1(power*np.log(z))))/power
                variance=float(p@(theta-float(p@theta))**2)
                lower=alpha*(1-s)**2*variance/2
                upper=alpha*(1-s)**2*variance/(2*s**(alpha+1))
                largest_equality_error=max(largest_equality_error,abs(actual-bound))
                largest_variance_violation=max(largest_variance_violation,lower-bound,bound-upper)
                assert abs(actual-bound)<1e-11
                assert lower<=bound+1e-11 and bound<=upper+1e-11
                assert abs(optimum.sum()-s*c)<1e-11
                sharpness.append({'alpha':alpha,'flows':d,'scale':s,
                                  'regret_per_M':float(actual),'sharp_bound':float(bound)})
    theta=np.linspace(.05,.35,40);p=np.full(40,1/40);s=.7
    z=s+(1-s)*theta;mean=float(p@z)
    log_bound=np.log(mean)-float(p@np.log(z))
    near=[]
    for alpha in [1-1e-6,1+1e-6]:
        power=1-alpha
        bound=(np.expm1(power*np.log(mean))-float(p@np.expm1(power*np.log(z))))/power
        assert abs(bound-log_bound)<1e-8
        near.append({'alpha':alpha,'bound':float(bound),'log_bound':float(log_bound)})
    result={'passed':True,'alpha_values':[.2,.5,1.,2.,4.],'independent_ray_cases':ray_cases,
            'sharpness_cases':len(sharpness),'maximum_relative_ray_error':largest_relative_ray_error,
            'maximum_sharpness_equality_error':largest_equality_error,
            'maximum_variance_violation':largest_variance_violation,
            'continuity_checks':near,'sharpness_checks':sharpness,
            'scope':'theoretical and small numerical supplement; large benchmark is log utility only'}
    root=Path(__file__).resolve().parent
    (root/'results'/'alpha_extension_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='sharpness_checks'},indent=2))


if __name__=='__main__':
    main()
