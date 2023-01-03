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
    coords = None

# Read the data, save it as a Pandas data frame that will be
# accessible to other functions in this module

def load_barriers(fn):
    '''
    Read barrier data exported from Excel, save it as a Pandas
    data frame.
    '''
    BF.data = pd.read_csv(fn)

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
