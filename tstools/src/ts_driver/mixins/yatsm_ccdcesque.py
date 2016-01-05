""" Mixin and functions for running CCDCesque through YATSM
"""
import inspect

from yatsm.algorithms import CCDCesque


# Hack for goof up in API previous to v0.6.0
def version_kwargs(d):
    """ Fix API calls for kwargs dict ``d`` that should have key ``estimator``
    """
    argspec = inspect.getargspec(CCDCesque.__init__)
    if 'estimator' in argspec.args:
        # Spec updated to estimator={object': ..., 'fit': {}}
        idx = [i for i, arg in enumerate(argspec.args)
               if arg == 'estimator'][0] - 1
        if isinstance(argspec.defaults[idx], dict):
            if not isinstance(d['estimator'], dict):
                d['estimator'] = {'object': d['estimator'], 'fit': {}}
        else:
            if isinstance(d['estimator'], dict):
                d['estimator'] = d['estimator']['object']
        return d
    elif 'lm' in argspec.args:
        new_key, old_key = 'lm', 'estimator'
        d[new_key] = d.pop(old_key)
        return d
    else:
        raise KeyError('Neither "lm" nor "estimator" are keys in '
                       'CCDCesque.__init__')
