"""Certified update actions and features available before a new problem is solved."""
from pathlib import Path
import os
for _thread_setting in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_thread_setting]='1'
import sys
import time
import numpy as np
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from certified_num import NUM, PriceRay, solve

TARGET = 1e-3
FEATURES = ['log_flows', 'log_links', 'route_length', 'shift_mean', 'shift_sd',
            'ratio_min', 'ratio_mean', 'ratio_sd', 'ratio_max', 'changed_fraction',
            'price_weighted_ratio', 'price_weighted_sd', 'active_price_fraction',
            'log_gap', 'ray_scale', 'candidate_utility_gain']


def make_cache(model, c0, x0, lam0):
    began = time.perf_counter()
    cache = PriceRay(model, lam0)
    theta = model.xi / (x0 + model.xi)
    weights = model.w / model.W
    cache.shift_mean = float(weights @ theta)
    cache.shift_sd = float(np.sqrt(weights @ (theta-cache.shift_mean)**2))
    cache.A_squared = model.A.multiply(model.A)
    cache.full_preparation_seconds = time.perf_counter()-began
    return cache


def features(model, cache, c0, c, lam0, query):
    ratio = c/c0
    weight = lam0*c0
    weight = weight/weight.sum()
    mean = float(weight @ ratio)
    return np.asarray([
        np.log10(model.d), np.log10(model.m), model.A.nnz/model.d,
        cache.shift_mean, cache.shift_sd, ratio.min(), ratio.mean(), ratio.std(),
        ratio.max(), np.mean(abs(ratio-1)>1e-10), mean,
        np.sqrt(weight @ (ratio-mean)**2), np.mean(lam0>1e-8),
        np.log10(max(query['gap_per_weight'], 1e-12)), query['scale'],
        (query['ray_lower']-query['anchor_lower'])/model.W], dtype=float)


def predict(record, z):
    """Use a portable, fitted linear or tree policy without estimator-call overhead."""
    if record['kind'] == 'constant':
        return bool(record['refine'])
    if record['kind'] == 'ridge':
        value = float(((z-np.array(record['mean']))/np.array(record['scale']))
                      @ np.array(record['coef']) + record['intercept'])
    else:
        node = 0
        while record['left'][node] != -1:
            node = (record['left'][node] if z[record['feature'][node]] <= record['threshold'][node]
                    else record['right'][node])
        value = record['value'][node]
    return value < record['decision_threshold']


def lightweight_refinement(model, cache, c0, c, lam0, query):
    """A local-price predictor and at most two eight-coordinate Newton corrections.

    Best primal and dual incumbents are retained independently. Every candidate
    is repaired against the actual new capacities. This is an iterative update,
    and its complete cost is charged to the method.
    """
    floor = 1e-12
    upper, lower = query['upper'], query['lower']
    best_x, best_lam = query['x'].copy(), query['lam'].copy()
    evaluations = 0
    steps = 0
    trace = [(upper-lower)/model.W]

    def retain(lam, value, rates):
        nonlocal upper, lower, best_x, best_lam
        candidate = model.repair(rates, c)
        utility = model.utility(candidate)
        if value < upper:
            upper, best_lam = value, lam.copy()
        if utility > lower:
            lower, best_x = utility, candidate
        gap = (upper-lower)/model.W
        if gap < -1e-9:
            raise FloatingPointError('Invalid update bound')
        trace.append(max(0., gap))

    proposal = np.maximum(floor, lam0*c0/c)
    value, grad, rates = model.dual(proposal, c)
    evaluations += 1
    retain(proposal, value, rates)
    ratio_gap = max(0., (upper-lower)/model.W)
    for _ in range(2):
        if (upper-lower)/model.W <= TARGET:
            break
        lam = best_lam.copy()
        value, grad, rates = model.dual(lam, c)
        evaluations += 1
        q = np.asarray(model.AT @ lam).ravel()
        weights = np.where(q*model.xi < model.w, model.w/q**2, 0.)
        diagonal = np.asarray(cache.A_squared @ weights).ravel()
        free = (lam > floor*1.01) | (grad < 0)
        indices = np.flatnonzero(free)
        if not len(indices):
            break
        ridge = 1e-8*max(float(diagonal.max()), 1e-12)
        scores = abs(grad[indices])/np.sqrt(diagonal[indices]+ridge)
        selected = indices[np.argsort(-scores, kind='stable')[:8]]
        rows = model.A[selected]
        hessian = (rows.multiply(weights) @ rows.T).toarray()
        direction = np.zeros(model.m)
        direction[selected] = np.linalg.solve(hessian+ridge*np.eye(len(selected)), -grad[selected])
        if float(grad @ direction) >= 0:
            direction[selected] = -grad[selected]/np.maximum(diagonal[selected], ridge)
        length = 1.
        accepted = False
        for _ in range(8):
            trial = np.maximum(floor, lam+length*direction)
            trial_value, _, trial_rates = model.dual(trial, c)
            evaluations += 1
            if trial_value <= value+1e-4*float(grad @ (trial-lam)):
                retain(trial, trial_value, trial_rates)
                steps += 1
                accepted = True
                break
            length *= .5
        if not accepted:
            break
    return {'x':best_x, 'lam':best_lam, 'upper':upper, 'lower':lower,
            'gap_per_weight':max(0., (upper-lower)/model.W),
            'refinement_evaluations':evaluations, 'refinement_steps':steps,
            'gap_after_ratio':ratio_gap, 'refinement_trace':trace}


def run_action(model, cache, c0, c, x0, lam0, method, policy=None):
    began = time.perf_counter()
    if method == 'ray_warm':
        result = solve(model, c, cache.scale(c)*lam0, TARGET, x0)
        result.update(seconds=time.perf_counter()-began, chose_refinement=False,
                      precheck_certified=False, light_certified=False,
                      refinement_evaluations=0, feature_seconds=0., prediction_seconds=0.)
        return result
    query = cache.query(c, x0)
    precheck = query['gap_per_weight'] <= TARGET
    selected = False
    feature_seconds = prediction_seconds = 0.
    if not precheck:
        if method == 'always_refine':
            selected = True
        elif method == 'heuristic':
            selected = float(np.std(c/c0)) > 1e-4
        elif method in {'learned', 'train_best'}:
            if policy['kind'] == 'constant':
                selected = bool(policy['refine'])
            else:
                started = time.perf_counter()
                z = features(model, cache, c0, c, lam0, query)
                feature_seconds = time.perf_counter()-started
                started = time.perf_counter()
                selected = predict(policy, z)
                prediction_seconds = time.perf_counter()-started
    state = query
    if selected:
        state = lightweight_refinement(model, cache, c0, c, lam0, query)
    light_certified = bool(selected and state['gap_per_weight'] <= TARGET)
    if state['gap_per_weight'] <= TARGET:
        result = {**state, 'converged':True, 'fg_evaluations':0, 'accepted_iterations':0,
                  'status':'certified after lightweight update' if selected else 'certified reuse'}
    else:
        result = solve(model, c, state['lam'], TARGET, state['x'])
    result.update(seconds=time.perf_counter()-began, chose_refinement=selected,
                  precheck_certified=precheck, light_certified=light_certified,
                  refinement_evaluations=state.get('refinement_evaluations', 0),
                  refinement_steps=state.get('refinement_steps', 0),
                  gap_after_ratio=state.get('gap_after_ratio', query['gap_per_weight']),
                  feature_seconds=feature_seconds, prediction_seconds=prediction_seconds)
    if model.overload(result['x'], c) > 1e-9:
        raise FloatingPointError('Update returned an infeasible allocation')
    return result
