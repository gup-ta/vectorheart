import hashlib
import json
import platform
import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

ADAPTER = 'toy.causal_intervention.v1'
LIMITATIONS = ['Synthetic simulation in a known configured world; not empirical evidence.', 'Normal 1.96 standard-error interval is an approximate 95% interval for the mean.', 'Compatibility uses whether each predicted mean lies inside that interval; no claim of real-world causality.']
class Parameters(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    data_generating_world: Literal['A', 'B'] = 'A'
    intervention_value: float = Field(default=2, ge=-5, le=5)
    sample_count: int = Field(default=1000, ge=100, le=5000, strict=True)
    seed: int = Field(default=42, ge=0, le=4294967295, strict=True)
def predictions(p):
    return {'A': {'mean': .8*p.intervention_value, 'variance': .36}, 'B': {'mean': 0., 'variance': 1.}}
def checksum(samples): return hashlib.sha256(json.dumps(samples, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
class NumericalResult(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    samples:list[float]=Field(min_length=100,max_length=5000)
    checksum:str
    mean:float
    std:float
    se:float
    confidence_interval:list[float]=Field(min_length=2,max_length=2)
    predictions:dict[str,dict[str,float]]
    compatible:dict[str,bool]
    environment:dict[str,str]
    source_type:Literal['simulation']
def simulate(raw):
    p = Parameters.model_validate(raw)
    rng = np.random.default_rng(p.seed)
    y = (.8*p.intervention_value + .6*rng.standard_normal(p.sample_count)) if p.data_generating_world == 'A' else rng.standard_normal(p.sample_count)
    samples = y.tolist()
    mean, std = float(np.mean(y)), float(np.std(y, ddof=1))
    se = std / np.sqrt(p.sample_count)
    interval = [float(mean-1.96*se), float(mean+1.96*se)]
    return {'samples': samples, 'checksum': checksum(samples), 'mean': mean, 'std': std, 'se': float(se), 'confidence_interval': interval, 'predictions': predictions(p), 'compatible': {k: interval[0] <= v['mean'] <= interval[1] for k,v in predictions(p).items()}, 'environment': {'python': platform.python_version(), 'numpy': np.__version__}, 'source_type': 'simulation'}
def validate_result(raw, parameters):
    raw=NumericalResult.model_validate(raw).model_dump()
    p = Parameters.model_validate(parameters)
    samples = np.asarray(raw['samples'], dtype=float)
    expected_mean = float(samples.sum()/len(samples))
    expected_std = float(np.sqrt(((samples-expected_mean)**2).sum()/(len(samples)-1)))
    se = expected_std/np.sqrt(len(samples))
    ci = [expected_mean-1.96*se, expected_mean+1.96*se]
    checks = {'sample_count': len(samples) == p.sample_count, 'finite': bool(np.isfinite(samples).all()) and all(np.isfinite(raw[k]) for k in ['mean','std','se']), 'checksum': raw['checksum'] == checksum(raw['samples']), 'statistics': bool(np.allclose([raw['mean'],raw['std'],raw['se']], [expected_mean,expected_std,se], rtol=1e-10)), 'interval': bool(np.allclose(raw['confidence_interval'], ci, rtol=1e-10)), 'analytical_predictions': raw['predictions'] == predictions(p), 'simulation_label': raw['source_type'] == 'simulation', 'compatibility': raw['compatible'] == {k: ci[0] <= v['mean'] <= ci[1] for k,v in predictions(p).items()}}
    if not all(checks.values()): raise ValueError('Computational validation failed: ' + str(checks))
    return checks
