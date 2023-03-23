# 
# Project
#
# A Project object has all the information used by the GUI to display
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

from targets import make_targets, DataSet

class Project:

    def __init__(self, fn, ds):
        '''
        Instantiate a Project object and initialize its attributes using
        data in a CSV file
        '''
        self.data = pd.read_csv(fn)
        self.targets = make_targets(ds)
        if ds == DataSet.TNC_OR:
            self.map_info = self._make_map_info()
            self.regions = self._make_region_list()
            self.totals = self._make_totals()
            self.climates = ['Current', 'Future']
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
    
    def _make_totals(self):
        '''
        Compute the total cost to repair all barriers in each region
        '''
        tf = self.data[['BARID','REGION','COST']].groupby('REGION').sum(numeric_only=True)
        return { x: tf.COST[x] for x in tf.index }

####################
#
# Unit tests
#
# Run the tests from the main project directory so pytest finds
# the test data:
#
#   $ pytest tidegates/project.py
#

class TestProject:

    @staticmethod
    def test_load():
        '''
        Load the test data frame, expect to find 6 rows, with single letter
        barrier IDs
        '''
        p = Project('static/test_wb.csv', DataSet.OPM)
        assert isinstance(p.data, pd.DataFrame)
        assert len(p.data) == 6
        assert list(p.data.BARID) == list('ABCDEF')

    @staticmethod
    def test_regions():
        '''
        The list of region names should be sorted from north to south
        '''
        p = Project('static/workbook.csv', DataSet.TNC_OR)
        assert len(p.regions) == 10
        assert p.regions[0] == 'Columbia'
        assert p.regions[-1] == 'Coquille'

    @staticmethod
    def test_map_info():
        '''
        The frame with map information should have 5 columns
        '''
        p = Project('static/workbook.csv', DataSet.TNC_OR)
        assert isinstance(p.map_info, pd.DataFrame)
        assert len(p.map_info) == len(p.data)
        assert list(p.map_info.columns) == ['id','region','type','x','y']

    @staticmethod
    def test_targets():
        '''
        There should be two sets of targets, each with 10 entries,
        and one entry for each target in the map.
        '''
        p = Project('static/workbook.csv', DataSet.TNC_OR)

        assert len(p.targets) == 2
        assert len(p.targets['Current']) == 10
        assert len(p.targets['Future']) == 10

        t = p.targets['Current']['CO']
        assert t.short == 'Coho'
        assert t.long == 'Fish habitat: Coho streams'
        assert t.habitat == 'sCO' 
        assert t.prepass == 'PREPASS_CO'
        assert t.postpass == 'POSTPASS'

        assert len(p.target_map) == 10
        assert p.target_map['Fish habitat: Coho streams'] == 'CO'
