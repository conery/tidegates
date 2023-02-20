# 
# Barriers
#
# Part of the Tide Gate Optimization Tool.  Defines the interface
# to the spreadsheet that has the information about the gates.
#

import pandas as pd
import numpy as np

class BF:
    '''
    The BF (barrier frame) class has attributes of the barrier
    data used by the GUI and by OptiPass.
    '''
    data = None
    map_info = None
    regions = None
    climates = ['Current', 'Future']
    targets = { }
    target_map = None

# Read the data, save it as a Pandas data frame that will be
# accessible to other functions in this module

def load_barriers(fn):
    '''
    Read barrier data exported from Excel, save it as a Pandas
    data frame.
    '''
    BF.data = pd.read_csv(fn)
    _make_map_info()
    _make_region_list()
    _make_targets()

def _make_map_info():
    '''
    Make a dataframe with attributes needed to display gates on a map.
    Map latitude and longitude columns in the input frame to Mercator
    coordinates, and copy the ID, region and barrier types so they can
    be displayed as tooltips.
    '''
    df = BF.data[['BARID','REGION','BarrierType']]
    R = 6378137.0
    BF.map_info = pd.concat([
        df, 
        np.radians(BF.data.POINT_X)*R, 
        np.log(np.tan(np.pi/4 + np.radians(BF.data.POINT_Y)/2)) * R
    ], axis=1)
    BF.map_info.columns = ['id', 'region', 'type', 'x', 'y']

def _make_region_list():
    '''
    Make a list of unique region names, sorted by latitude, so regions
    are displayed in order from north to south
    '''
    df = BF.data[['BARID','REGION','POINT_Y']]
    m = df.groupby('REGION').mean(numeric_only=True).sort_values(by='POINT_Y',ascending=False)
    BF.regions = list(m.index)

def _make_targets():
    '''
    Create dictionaries with target records for each climate scenario,
    and a dictionary that maps long descriptions to target IDs
    '''
    BF.targets['Current'] = dict(fish_targets)
    BF.targets['Current'] |= current_infrastructure_targets
    BF.targets['Future'] = dict(fish_targets)
    BF.targets['Future'] |= future_infrastructure_targets
    BF.target_map = { BF.targets['Current'][x].long: x for x in BF.targets['Current'].keys()}

####################
#
# Restoration targets
#
# A target is defined by a short description (used in output tables), a long
# description (displayed in the GUI), and names of spreadsheet columns that
# have the upstream habitat, current passability, and post-restoration passability.

from collections import namedtuple

Target = namedtuple('Target', ['long', 'short', 'habitat', 'prepass', 'postpass', 'unscaled'])

# Panel uses the long description in checkbox values; we need to map them to
# target IDs.

CO = 'Fish habitat: Coho streams'
CH = 'Fish habitat: Chinook streams'
ST = 'Fish habitat: Steelhead streams'
CT = 'Fish habitat: Cutthroat streams'
CU = 'Fish habitat: Chum streams'
FI = 'Fish habitat: Inundation'
AG = 'Agriculture'
RR = 'Roads & Railroads'
BL = 'Buildings'
PS = 'Public-Use Structures'

fish_targets = {
    'CO':  Target(CO, 'Coho', 'sCO', 'PREPASS_CO', 'POSTPASS', 'Coho_salmon'),
    'CH':  Target(CH, 'Chinook', 'sCH', 'PREPASS_CH', 'POSTPASS', 'Chinook_salmon'),
    'ST':  Target(ST, 'Steelhead', 'sST', 'PREPASS_ST', 'POSTPASS', 'Steelhead'),
    'CT':  Target(CT, 'Cutthroat', 'sCT', 'PREPASS_CT', 'POSTPASS', 'Cutthroat_Trout'),
    'CU':  Target(CU, 'Chum', 'sCU', 'PREPASS_CU', 'POSTPASS', 'Chum'),
}

current_infrastructure_targets = {
    'FI': Target(FI, 'Inund', 'sInundHab_Current', 'PREPASS_FISH', 'POSTPASS', 'InundHab_Current'),
    'AG': Target(AG, 'Agric', 'sAgri_Current', 'PREPASS_AgrInf', 'POSTPASS', 'Agri_Current'),
    'RR': Target(RR, 'Roads', 'sRoadRail_Current', 'PREPASS_AgrInf', 'POSTPASS', 'RoadRail_Current'),
    'BL': Target(BL, 'Bldgs', 'sBuilding_Current', 'PREPASS_AgrInf', 'POSTPASS', 'Building_Current'),
    'PS': Target(PS, 'Public', 'sPublicUse_Current', 'PREPASS_AgrInf', 'POSTPASS', 'PublicUse_Current'),
}

future_infrastructure_targets = {
    'FI': Target(FI, 'Inund', 'sInundHab_Future', 'PREPASS_FISH', 'POSTPASS', 'InundHab_Future'),
    'AG': Target(AG, 'Agric', 'sAgri_Future', 'PREPASS_AgrInf', 'POSTPASS', 'Agri_Future'),
    'RR': Target(RR, 'Roads', 'sRoadRail_Future', 'PREPASS_AgrInf', 'POSTPASS', 'RoadRail_Future'),
    'BL': Target(BL, 'Bldgs', 'sBuilding_Future', 'PREPASS_AgrInf', 'POSTPASS', 'Building_Future'),
    'PS': Target(PS, 'Public', 'sPublicUse_Future', 'PREPASS_AgrInf', 'POSTPASS', 'PublicUse_Future'),
}


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

    @staticmethod
    def test_load():
        '''
        Load the test data frame, expect to find 30 rows.
        '''
        load_barriers('static/test_barriers.csv')
        assert isinstance(BF.data, pd.DataFrame)
        assert len(BF.data) == 30

    @staticmethod
    def test_regions():
        '''
        The list of region names should be sorted from north to south
        '''
        load_barriers('static/test_barriers.csv')
        assert BF.regions == ['Umpqua', 'Coos', 'Coquille']

    @staticmethod
    def test_map_info():
        '''
        The frame with map information should have 5 columns
        '''
        load_barriers('static/test_barriers.csv')
        assert isinstance(BF.map_info, pd.DataFrame)
        assert len(BF.map_info) == len(BF.data)
        assert list(BF.map_info.columns) == ['id','region','type','x','y']

    @staticmethod
    def test_target_columns():
        '''
        Make sure the column names in the Target objects are the same as
        the column names in the data file
        '''
        load_barriers('static/test_barriers.csv')
        for s in ['Current', 'Future']:
            for t in BF.targets[s].values():
                assert t.habitat in BF.data.columns
                assert t.prepass in BF.data.columns
                assert t.postpass in BF.data.columns
                assert t.unscaled in BF.data.columns

    @staticmethod
    def test_targets():
        '''
        There should be two sets of targets, each with 10 entries,
        and one entry for each target in the map.
        '''
        load_barriers('static/test_barriers.csv')
        assert len(BF.targets) == 2
        assert len(BF.targets['Current']) == 10
        assert len(BF.targets['Future']) == 10

        t = BF.targets['Current']['CO']
        assert t.short == 'Coho'
        assert t.long == CO
        assert t.habitat == 'sCO' 
        assert t.prepass == 'PREPASS_CO'
        assert t.postpass == 'POSTPASS'

        assert len(BF.target_map) == 10
        assert BF.target_map[CO] == 'CO'

    @staticmethod
    def test_colnames():
        '''
        Make sure the column names in the Target objects exist in the
        data frame.
        '''
        load_barriers('static/test_barriers.csv')
        for c in ['Current', 'Future']:
            for t in BF.targets[c].values():
                assert t.habitat in BF.data.columns
                assert t.prepass in BF.data.columns
                assert t.postpass in BF.data.columns
