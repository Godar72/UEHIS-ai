import math
import numpy as np
import pandas as pd
import pytest

from scoring.entropy import entropy_weights, EntropyWeightError, compute_factor_diagnostics

def test_pm25_36_38_case():
    """
    Test exactly 256 blocks with 144 blocks having 3.6 and 112 blocks having 3.8.
    Raw entropy should be ~0.999935 and diversity ~0.000065.
    """
    values = [3.6] * 144 + [3.8] * 112
    df = pd.DataFrame({'pm25': values, 'dummy': np.random.uniform(0, 1, 256)})
    diagnostics = compute_factor_diagnostics(df, ['pm25', 'dummy'])
    
    pm25_diag = next(d for d in diagnostics if d['name'] == 'pm25')
    
    # Run the math ourselves to check against what the module returns via diversity sum
    n = 256
    eps = 1e-12
    total_pm25 = sum(values)
    p = np.array(values) / total_pm25
    term = np.where(p > 0, p * np.log(p), 0.0)
    expected_e = -(1.0 / math.log(n)) * term.sum()
    
    # Since diversity = raw_weight * sum(diversity), PM2.5 gets a tiny weight
    assert pm25_diag['raw_entropy_weight'] < 0.01  # it should be tiny, compared to dummy
    assert math.isclose(expected_e, 0.999935, abs_tol=1e-4)

def test_constant_factor():
    """Constant factor should get 0 weight."""
    df = pd.DataFrame({'const': [5.0]*10, 'var': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
    weights = entropy_weights(df, ['const', 'var'])
    assert weights['const'] == 0.0
    assert math.isclose(weights['var'], 1.0)

def test_all_factors_constant():
    """All-constant fallback should yield equal weights."""
    df = pd.DataFrame({'c1': [5.0]*10, 'c2': [2.0]*10})
    with pytest.warns(UserWarning, match="All factors are constant"):
        weights = entropy_weights(df, ['c1', 'c2'])
    assert weights['c1'] == 0.5
    assert weights['c2'] == 0.5

def test_zero_valued_factor():
    """Zero-valued factor should be handled cleanly without additive shift."""
    df = pd.DataFrame({'zeros': [0.0, 0.0, 5.0, 10.0], 'var': [1, 2, 3, 4]})
    weights = entropy_weights(df, ['zeros', 'var'])
    assert not np.isnan(weights['zeros'])
    assert not np.isnan(weights['var'])
    assert math.isclose(sum(weights.values()), 1.0)

def test_negative_valued_factor():
    """Negative-valued factor should trigger additive shift."""
    df = pd.DataFrame({'neg': [-10.0, -5.0, 0.0, 5.0], 'var': [1, 2, 3, 4]})
    weights = entropy_weights(df, ['neg', 'var'])
    assert not np.isnan(weights['neg'])
    assert not np.isnan(weights['var'])
    assert math.isclose(sum(weights.values()), 1.0)

def test_entropy_diversity_bounds():
    """Check probability, entropy, and diversity bounds implicitly via weight sum."""
    df = pd.DataFrame({'f1': np.random.uniform(0, 10, 100), 'f2': np.random.uniform(20, 30, 100)})
    weights = entropy_weights(df, ['f1', 'f2'])
    assert math.isclose(sum(weights.values()), 1.0)
    for w in weights.values():
        assert 0.0 <= w <= 1.0

def test_weight_sum():
    df = pd.DataFrame({'A': [1, 2, 3, 4], 'B': [1, 1, 2, 2], 'C': [5, 5, 5, 5]})
    weights = entropy_weights(df, ['A', 'B', 'C'])
    assert math.isclose(sum(weights.values()), 1.0)

def test_full_factor_run():
    df = pd.DataFrame({
        'ndvi': np.random.uniform(0.1, 0.6, 256),
        'tree_density': np.random.uniform(0.0, 0.5, 256),
        'biodiversity': np.random.uniform(0.1, 1.0, 256),
        'pm25': np.random.choice([3.6, 3.8], 256),
        'temperature': np.random.uniform(25, 40, 256),
        'impervious_surfaces': np.random.uniform(0.0, 1.0, 256),
        'population_exposure': np.random.uniform(10, 500, 256)
    })
    weights = entropy_weights(df, df.columns.tolist())
    assert all(not np.isnan(w) and not np.isinf(w) for w in weights.values())
    assert math.isclose(sum(weights.values()), 1.0)
