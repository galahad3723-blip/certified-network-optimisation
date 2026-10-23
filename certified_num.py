"""Research implementation of certified reuse for hard-capacity NUM.

Weak-duality certificates, price-ray optimisation and pathwise feasibility
repair are standard building blocks. Novelty of their use here is not assumed.
"""
from __future__ import annotations
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
from dataclasses import dataclass
import collections
import time
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from scipy import sparse
from scipy.optimize import minimize


def topology(path):
    ns={'g':'http://graphml.graphdrawing.org/xmlns'}
    doc=ET.parse(path)
    nodes=sorted(n.attrib['id'] for n in doc.findall('.//g:node',ns))
    adjacency={n:set() for n in nodes}
    raw=doc.findall('.//g:edge',ns)
    self_loops=0
    for edge in raw:
        a,b=edge.attrib['source'],edge.attrib['target']
        if a==b:self_loops+=1;continue
        adjacency[a].add(b);adjacency[b].add(a)
    remaining=set(nodes);components=[]
    while remaining:
        first=min(remaining);seen={first};queue=[first]
        for v in queue:
            for u in sorted(adjacency[v]):
                if u not in seen:seen.add(u);queue.append(u)
        remaining-=seen;components.append(seen)
    keep=sorted(components,key=lambda z:(-len(z),sorted(z)))[0]
    labels=sorted(keep);index={n:i for i,n in enumerate(labels)}
    edges=sorted({tuple(sorted((index[a],index[b]))) for a in keep for b in adjacency[a] if b in keep})
    info={'name':Path(path).stem,'raw_nodes':len(nodes),'raw_edges':len(raw),
          'used_nodes':len(labels),'simple_undirected_edges':len(edges),
          'components':len(components),'self_loops_removed':self_loops,
          'removed_nodes':len(nodes)-len(labels),
          'preprocessing':'undirected simple graph; largest component; deterministic shortest paths'}
    return len(labels),edges,info


def routing(n,edges,d,seed):
    adjacency=[[] for _ in range(n)];directed=[]
    for a,b in edges:
        adjacency[a].append(b);adjacency[b].append(a)
        directed.extend([(a,b),(b,a)])
    edge_index={e:i for i,e in enumerate(directed)}
    paths={}
    for a in range(n):
        pred={a:None};queue=collections.deque([a])
        while queue:
            v=queue.popleft()
            for u in sorted(adjacency[v]):
                if u not in pred:pred[u]=v;queue.append(u)
        for b in range(n):
            if a==b:continue
            steps=[];v=b
            while pred[v] is not None:
                u=pred[v];steps.append(edge_index[(u,v)]);v=u
            paths[a,b]=steps
    rng=np.random.default_rng(seed)
    rows=[];cols=[]
    for j in range(d):
        a,b=map(int,rng.choice(n,2,replace=False))
        for row in paths[a,b]:rows.append(row);cols.append(j)
    A=sparse.csr_matrix((np.ones(len(rows)),(rows,cols)),shape=(len(directed),d))
    used=np.asarray(A.sum(axis=1)).ravel()>0
    return A[used].tocsr(),np.array(directed)[used]


@dataclass
class NUM:
    A:sparse.csr_matrix
    w:np.ndarray
    xi:np.ndarray

    def __post_init__(self):
        self.AT=self.A.T.tocsr();self.m,self.d=self.A.shape
        self.W=float(self.w.sum())
        if np.any(self.w<=0) or np.any(self.xi<0):raise ValueError('Invalid utility parameters')
        if np.any(np.diff(self.AT.indptr)==0):raise ValueError('Empty route')

    def utility(self,x):
        shifted=x+self.xi
        if np.any(shifted<=0):return -float('inf')
        return float(self.w@np.log(shifted))

    def conjugate(self,q):
        if np.any(q<=0):raise ValueError('Route prices must be positive')
        active=q*self.xi<self.w
        answer=np.empty(self.d)
        answer[active]=self.w[active]*(np.log(self.w[active]/q[active])-1)+self.xi[active]*q[active]
        answer[~active]=self.w[~active]*np.log(self.xi[~active])
        return answer

    def rates(self,q):return np.maximum(0,self.w/q-self.xi)

    def dual(self,lam,c):
        q=np.asarray(self.AT@lam).ravel()
        x=self.rates(q)
        return float(c@lam+self.conjugate(q).sum()),np.asarray(c-self.A@x),x

    def repair(self,x,c):
        """One-pass routewise downscaling; not a Euclidean projection."""
        xx=np.maximum(0,np.asarray(x));load=np.asarray(self.A@xx).ravel()
        ratio=np.ones(self.m)
        positive=load>0
        ratio[positive]=np.minimum(1,c[positive]/load[positive])
        factor=np.minimum.reduceat(ratio[self.AT.indices],self.AT.indptr[:-1])
        repaired=xx*factor/(1+16*np.finfo(float).eps)
        return repaired

    def overload(self,x,c):return float(max(0,np.max(np.asarray(self.A@x)/c-1)))


class ReachedCertificate(Exception):pass


def solve(model,c,initial_lam,tol,initial_x=None,maxiter=3000,refine=False):
    """L-BFGS-B with the same feasible-primal/dual test at every FG evaluation."""
    began=time.perf_counter();floor=1e-12
    best_upper=float('inf');best_lower=-float('inf')
    best_x=None;best_lam=None;calls=0;accepted_steps=0
    trace=[]
    if initial_x is not None:
        best_x=model.repair(initial_x,c);best_lower=model.utility(best_x)
    def objective(lam):
        nonlocal best_upper,best_lower,best_x,best_lam,calls
        calls+=1
        value,grad,xq=model.dual(lam,c)
        candidate=model.repair(xq,c);u=model.utility(candidate)
        if value<best_upper:best_upper=value;best_lam=lam.copy()
        if u>best_lower:best_lower=u;best_x=candidate
        gap=(best_upper-best_lower)/model.W
        if gap < -1e-9:raise FloatingPointError('Weak-duality violation')
        trace.append([calls,max(0,gap)])
        if gap<=tol:raise ReachedCertificate
        return value,grad
    def callback(_):
        nonlocal accepted_steps
        accepted_steps+=1
    lam=np.maximum(floor,np.asarray(initial_lam)).copy();status='iteration cap'
    try:
        result=minimize(objective,lam,method='L-BFGS-B',jac=True,
                        bounds=[(floor,None)]*model.m,callback=callback,
                        options={'maxiter':maxiter,'maxfun':maxiter*15,'maxls':80,
                                 'ftol':1e-15,'gtol':1e-11,'maxcor':30})
        lam=result.x.copy();status=str(result.message)
    except ReachedCertificate:
        status='certified'
        lam=best_lam.copy()
    # References may use extra safeguarded Newton steps; measured methods do not.
    if refine and (best_upper-best_lower)/model.W>tol:
        for _ in range(100):
            value,g,xq=model.dual(lam,c)
            q=np.asarray(model.AT@lam).ravel()
            weight=np.where(q*model.xi<model.w,model.w/q**2,0)
            H=(model.A@sparse.diags(weight)@model.AT).toarray()
            free=(lam>floor*1.01)|(g<0)
            if not free.any():break
            hf=H[np.ix_(free,free)]
            ridge=1e-11*max(1,float(np.max(np.diag(hf))))
            step=np.zeros(model.m)
            step[free]=np.linalg.solve(hf+ridge*np.eye(free.sum()),-g[free])
            if g@step>=0:step[free]=-g[free]/np.maximum(1,np.diag(hf))
            length=1.;accepted=False
            for _ in range(70):
                trial=np.maximum(floor,lam+length*step)
                if model.dual(trial,c)[0]<=value+1e-4*float(g@(trial-lam)):
                    lam=trial;accepted=True;break
                length*=.5
            if not accepted:break
            try:objective(lam)
            except ReachedCertificate:status='certified after reference refinement';break
    gap=max(0,(best_upper-best_lower)/model.W)
    return {'x':best_x,'lam':best_lam,'upper':best_upper,'lower':best_lower,
            'gap_per_weight':gap,'converged':gap<=tol,'fg_evaluations':calls,
            'accepted_iterations':accepted_steps,'seconds':time.perf_counter()-began,
            'status':status,'trace':trace}


@dataclass
class PriceRay:
    model:NUM
    lam:np.ndarray

    def __post_init__(self):
        began=time.perf_counter()
        self.q=np.asarray(self.model.AT@self.lam).ravel()
        if np.any(self.q<=0):raise ValueError('Invalid anchor price')
        alpha=self.model.xi*self.q/self.model.w
        order=np.argsort(alpha,kind='stable')
        self.alpha=alpha[order]
        self.prefix_w=np.cumsum(self.model.w[order])
        self.prefix_h=np.cumsum((self.model.xi*self.q)[order])
        prev_w=np.r_[0.,self.prefix_w[:-1]]
        prev_h=np.r_[0.,self.prefix_h[:-1]]
        self.breakpoints=np.maximum.accumulate(self.alpha*prev_w-prev_h)
        self.phi=self.model.conjugate(self.q).sum()
        self.preparation_seconds=time.perf_counter()-began

    def scale(self,c):
        """Exact active-set water filling on the fixed price ray."""
        gamma=float(c@self.lam)
        if gamma<=0:raise ValueError('Capacities and anchor prices must be positive')
        k=min(len(self.prefix_w),int(np.searchsorted(self.breakpoints,gamma,side='right')))
        if k==0:k=1
        b=(gamma+self.prefix_h[k-1])/self.prefix_w[k-1]
        return 1/b

    def query(self,c,x0):
        began=time.perf_counter();t=self.scale(c)
        x_anchor=self.model.repair(x0,c)
        x_ray=self.model.repair(self.model.rates(t*self.q),c)
        ua=self.model.utility(x_anchor);ur=self.model.utility(x_ray)
        x=x_anchor if ua>=ur else x_ray;u=max(ua,ur)
        gamma=float(c@self.lam)
        fixed=gamma+self.phi
        upper=t*gamma+float(self.model.conjugate(t*self.q).sum())
        if upper>fixed+1e-9*max(1,abs(fixed)):raise FloatingPointError('Ray minimisation failed')
        gap=(upper-u)/self.model.W
        if gap < -1e-9:raise FloatingPointError('Invalid reuse certificate')
        return {'x':x,'lam':t*self.lam,'upper':upper,'lower':u,
                'gap_per_weight':max(0,gap),'fixed_price_gap_per_weight':max(0,(fixed-ua)/self.model.W),
                'anchor_lower':ua,'ray_lower':ur,'scale':t,'seconds':time.perf_counter()-began}


def run_method(model,c,anchor,cache,method,tol):
    began=time.perf_counter();skipped=False;precheck=0.
    if method=='reuse':
        q=cache.query(c,anchor['x']);precheck=q['seconds']
        if q['gap_per_weight']<=tol:
            out={**q,'converged':True,'fg_evaluations':0,'accepted_iterations':0,'status':'reuse certified'}
            skipped=True
        else:
            out=solve(model,c,q['lam'],tol,q['x'])
    else:
        if method=='cold':initial=np.full(model.m,0.2)
        elif method=='warm':initial=anchor['lam']
        elif method=='ray_warm':initial=cache.scale(c)*anchor['lam']
        else:raise ValueError(method)
        out=solve(model,c,initial,tol,anchor['x'])
    out.update(seconds=time.perf_counter()-began,precheck_seconds=precheck,skipped=skipped)
    return out
