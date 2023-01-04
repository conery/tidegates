# 
# Barriers
#
# Part of the Tide Gate Optimization Tool.  Defines the interface
# to the spreadsheet that has the information about the gates.
#

import pandas as pd

class BF:
    '''
    The BF (barrier frame) class has attributes of the barrier
    data used by the GUI and by OptiPass.
    '''
    data = None
    regions = None
    map_info = None

# Read the data, save it as a Pandas data frame that will be
# accessible to other functions in this module

def load_barriers(fn):
    '''
    Read barrier data exported from Excel, save it as a Pandas
    data frame.
    '''
    BF.data = pd.read_csv(fn)
    BF.regions = list(BF.data.groupby('region').mean().sort_values(by='lat',ascending=False).index)
    BF.map_info = BF.data[['barid','region','barriertype','lat','lon']]


####################
#
# Unit tests
#
# Run the tests from the main project directory so pytest finds
# the test data:
#
#   $ pytest tidegates/barriers.py
#

import pytest

class TestBarriers:

    def test_load(self):
        '''
        Load the test data frame, expect to find 30 rows.
        '''
        load_barriers('static/test_barriers.csv')
        assert isinstance(BF.data, pd.DataFrame)
        assert len(BF.data) == 30

    def test_regions(self):
        '''
        The list of region names should be sorted from north to south
        '''
        load_barriers('static/test_barriers.csv')
        assert BF.regions == ['Umpqua', 'Coos', 'Coquille']

    def test_map_info(self):
        '''
        The frame with map information should have 5 columns
        '''
        load_barriers('static/test_barriers.csv')
        assert isinstance(BF.map_info, pd.DataFrame)
        assert len(BF.map_info) == len(BF.data)
        assert list(BF.map_info.columns) == ['barid','region','barriertype','lat','lon']
