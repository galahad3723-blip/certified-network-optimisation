"""Independent numerical checks of algebra, ray active sets and counterexamples."""
from pathlib import Path
import json
from certified_num import NUM,PriceRay
import numpy as np
from scipy import sparse
from scipy.optimize import minimize_scalar


def main():
    rng=np.random.default_rng(20261022)
    scalar_error=0.;duality_margin=float('inf');gradient_error=0.
    for j in range(150):
        d=50;A=sparse.csr_matrix(np.eye(d));w=np.exp(rng.normal(0,.5,d))
        xi=rng.uniform(0,2,d);xi[rng.random(d)<.15]=0
        model=NUM(A,w,xi);lam=np.exp(rng.normal(0,1,d));c=np.exp(rng.normal(0,1,d))
        cache=PriceRay(model,lam);t=cache.scale(c)
        reference=minimize_scalar(lambda z:model.dual(np.exp(z)*lam,c)[0],
                                  bounds=(-15,15),method='bounded',options={'xatol':1e-12})
        f=model.dual(t*lam,c)[0]
        scalar_error=max(scalar_error,abs(f-reference.fun)/max(1,abs(reference.fun)))
        assert scalar_error<1e-10
        x=model.repair(rng.uniform(.01,2,d),c)
        duality_margin=min(duality_margin,model.dual(lam,c)[0]-model.utility(x))
        direction=rng.normal(size=d);direction/=np.linalg.norm(direction)
        step=1e-6*min(1,float(np.min(lam)))
        v,g,_=model.dual(lam,c)
        fd=(model.dual(lam+step*direction,c)[0]-model.dual(lam-step*direction,c)[0])/(2*step)
        gradient_error=max(gradient_error,abs(fd-g@direction)/max(1,abs(fd)))
    assert duality_margin>=-1e-10
    assert gradient_error<1e-5
    tight=[]
    for d in [2,5,40]:
        w=np.exp(rng.normal(0,.5,d));theta=np.linspace(.1,.5,d)
        xi=w*theta;x0=w-xi;c0=np.array([x0.sum()])
        model=NUM(sparse.csr_matrix(np.ones((1,d))),w,xi)
        for s in [.6,.8,.95]:
            cache=PriceRay(model,np.ones(1));t=cache.scale(s*c0)
            xstar=model.rates(t*np.ones(d))
            assert np.min(xstar)>0
            exact_regret=(model.utility(xstar)-model.utility(s*x0))/model.W
            z=s+(1-s)*theta;p=w/model.W
            jensen=np.log(p@z)-p@np.log(z)
            variance=p@(theta-p@theta)**2
            variance_bound=(1-s)**2*variance/(2*s*s)
            assert abs(exact_regret-jensen)<1e-12
            assert jensen<=variance_bound+1e-12
            tight.append({'d':d,'s':s,'regret_per_weight':exact_regret,
                          'jensen_bound':float(jensen),'variance_bound':float(variance_bound)})
    counter=[]
    model=NUM(sparse.eye(2,format='csr'),np.ones(2),np.zeros(2))
    cache=PriceRay(model,np.ones(2))
    for r in [.5,.1,.01,1e-5]:
        caps=np.array([r,1.]);query=cache.query(caps,np.ones(2))
        exact=np.log(r);gap=np.log((1+r)**2/(4*r))/2
        assert abs(model.utility(query['x'])-exact)<1e-12
        assert abs(query['gap_per_weight']-gap)<1e-12
        counter.append({'small_capacity_ratio':r,'actual_regret':0.,'certificate_per_weight':gap})
    results={'ray_trials':150,'max_ray_objective_relative_error':scalar_error,
             'minimum_weak_duality_margin':duality_margin,
             'max_dual_directional_gradient_error':gradient_error,
             'sharp_single_link_checks':tight,'optimal_but_uncertified_counterexamples':counter,
             'interpretation':'Numerical validation supplements the written proofs, not novelty or interval-arithmetic certification.'}
    out=Path('results');out.mkdir(exist_ok=True)
    (out/'theory_validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
