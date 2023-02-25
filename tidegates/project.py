# 
# Barriers
#
# A Barriers object has all the information used by the GUI to display
# a set of tide gates.  The constructor is passed the name of a CSV file
# that has a list of all the barriers and uses it to define attributes:
#
#   data: a copy of the original data, in the form of a Pandas data frame
#   map_info:  a table containging geographical coordinates of the gates
#   regions:  a list of the unique region names in the file
#   climates:  a list of climate scenarios
# 
# The constructor aslo gets region-specific restoration target information
# from the targets module and saves it in the object.
#
#   targets:     a dictionary of restoration target attributes for each 
#                climate scenario
#   target_map:  a dictionary that associates the target name displayed in
#                the GUI with the target's ID
#

import pandas as pd
import numpy as np

from targets import make_targets

class Barriers:

    def __init__(self, fn):
        '''
        Instantiate a Barriers object and initialize its attributes using
        data in a CSV file
        '''
        self.data = pd.read_csv(fn)
        self.map_info = self._make_map_info()
        self.regions = self._make_region_list()
        self.climates = ['Current', 'Future']
        self.targets = make_targets()

        # The target names are the same in each scenario, we can use either
        # one to build this map
        dct = self.targets['Current']
        self.target_map = { dct[x].long: x for x in dct.keys()}

    def _make_map_info(self):
        '''
        Make a dataframe with attributes needed to display gates on a map.
        Map latitude and longitude columns in the input frame to Mercator
        coordinates, and copy the ID, region and barrier types so they can
        be displayed as tooltips.
        '''
        df = self.data[['BARID','REGION','BarrierType']]
        R = 6378137.0
        map_info = pd.concat([
            df, 
            np.radians(self.data.POINT_X)*R, 
            np.log(np.tan(np.pi/4 + np.radians(self.data.POINT_Y)/2)) * R
        ], axis=1)
        map_info.columns = ['id', 'region', 'type', 'x', 'y']
        return map_info

    def _make_region_list(self):
        '''
        Make a list of unique region names, sorted by latitude, so regions
        are displayed in order from north to south
        '''
        df = self.data[['BARID','REGION','POINT_Y']]
        mf = df.groupby('REGION').mean(numeric_only=True).sort_values(by='POINT_Y',ascending=False)
        return list(mf.index)


####################
#
# Unit tests
#
# Run the tests from the main project directory so pytest finds
# the test data:
#
#   $ pytest tidegates/barriers.py
#

class TestBarriers:

    @staticmethod
    def test_load():
        '''
        Load the test data frame, expect to find 30 rows.
        '''
        bf = Barriers('static/test_barriers.csv')
        assert isinstance(bf.data, pd.DataFrame)
        assert len(bf.data) == 30

    @staticmethod
    def test_regions():
        '''
        The list of region names should be sorted from north to south
        '''
        bf = Barriers('static/test_barriers.csv')
        assert bf.regions == ['Umpqua', 'Coos', 'Coquille']

    @staticmethod
    def test_map_info():
        '''
        The frame with map information should have 5 columns
        '''
        bf = Barriers('static/test_barriers.csv')
        assert isinstance(bf.map_info, pd.DataFrame)
        assert len(bf.map_info) == len(bf.data)
        assert list(bf.map_info.columns) == ['id','region','type','x','y']

    @staticmethod
    def test_target_columns():
        '''
        Make sure the column names in the Target objects are the same as
        the column names in the data file
        '''
        bf = Barriers('static/test_barriers.csv')
        for s in ['Current', 'Future']:
            for t in bf.targets[s].values():
                assert t.habitat in bf.data.columns
                assert t.prepass in bf.data.columns
                assert t.postpass in bf.data.columns
                assert t.unscaled in bf.data.columns

    @staticmethod
    def test_targets():
        '''
        There should be two sets of targets, each with 10 entries,
        and one entry for each target in the map.
        '''
        bf = Barriers('static/test_barriers.csv')
        assert len(bf.targets) == 2
        assert len(bf.targets['Current']) == 10
        assert len(bf.targets['Future']) == 10

        t = bf.targets['Current']['CO']
        assert t.short == 'Coho'
        assert t.long == 'Fish habitat: Coho streams'
        assert t.habitat == 'sCO' 
        assert t.prepass == 'PREPASS_CO'
        assert t.postpass == 'POSTPASS'

        assert len(bf.target_map) == 10
        assert bf.target_map['Fish habitat: Coho streams'] == 'CO'
