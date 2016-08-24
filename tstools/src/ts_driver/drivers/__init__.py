""" Timeseries drivers
"""
from collections import OrderedDict

DRIVERS = OrderedDict((
    ('StackedTimeSeries', 'timeseries_stacked'),
    ('CCDCTimeSeries', 'timeseries_ccdc'),
    ('YATSMTimeSeries', 'timeseries_yatsm'),
    ('YATSMMetTimeSeries', 'timeseries_yatsm_met'),
    ('YATSMLandsatPALSARTS', 'timeseries_opticalradar'),
))

for name, val in DRIVERS.items():
    DRIVERS[name] = 'tstools.ts_driver.drivers.' + val
