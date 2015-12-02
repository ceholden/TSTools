""" Utility for reading / running CCDCesque YATSM implementation
"""
import numpy as np


class YATSMResults(object):

    # Driver controls
    _calculate_live = True
    _consecutive = 5
    _min_obs = 16
    _threshold = 4.0
    _enable_min_rmse = True
    _min_rmse = 100
    _design = '1 + x + harm(x, 1)'
    _test_indices = np.array([2, 3, 4, 5])
    _dynamic_rmse = True
    _screen_crit = 400.0
    _remove_noise = True
    _reverse = False
    _robust_results = False
    _commit_test = False
    _commit_alpha = 0.01

    # Requires YATSM>=v0.5.0
    _regression_type = 'sklearn_Lasso20'
    controls_title = 'YATSM Algorithm Options'
    controls = [
        '_calculate_live',
        '_consecutive',
        '_min_obs',
        '_threshold',
        '_enable_min_rmse',
        '_min_rmse',
        '_design',
        '_test_indices',
        '_dynamic_rmse',
        '_screen_crit',
        '_remove_noise',
        '_reverse',
        '_regression_type',
        '_robust_results',
        '_commit_test',
        '_commit_alpha']
    controls_names = [
        'Calculate live',
        'Consecutive',
        'Min Observations',
        'Threshold',
        'Use min RMSE?',
        'Min RMSE',
        'Design',
        'Test indices',
        'Dynamic RMSE',
        'Screening critical value',
        'Remove noise',
        'Run in reverse',
        'Regression type',
        'Robust results',
        'Commission test',
        'Commission test alpha']
