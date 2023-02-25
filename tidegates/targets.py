# 
# Restoration Targets 
# 
# This file is basically a configuration file, a place to define the names
# and attribures of restoration targets specific to a set of data set.
#
# A Target object has two kinds of information about a restoration target:
#   * names that are displayed in the GUI and appear in data tables and plots
#   * column names that identify which columns in the main data file are
#     associated with the target.
#
# An application can call make_targets to get a dictionary that associates
# target IDs with Target objects.
#

from collections import namedtuple
from enum import Enum, auto

# Data sets defined in this file:

class DataSet(Enum):
    OPM = auto()                # Sample data in the OptiPass User Manual
    TNC_OR = auto()             # Nature Conservancy Southern Oregon Coast

Target = namedtuple('Target', ['abbrev', 'long', 'short', 'habitat', 'prepass', 'postpass', 'unscaled'])

# Make the targets for the Southern Oregon Coast 

def make_targets(ds: DataSet) -> dict:
    '''
    Create dictionaries that map two-letter target IDs to complete target
    descriptioms.  The TNC data set has two dictionaries, one for each
    climate scenario.
    '''
    if ds == DataSet.TNC_OR:
        current = dict(fish_targets)
        current |= current_infrastructure_targets
        future = dict(fish_targets)
        future |= future_infrastructure_targets
        return {
            'Current': current,
            'Future': future,
        }
    else:
        return opm_targets

# Restoration targets from the OptiPass Manual.  Fields we don't 
# used are filled with empty strings.

opm_targets = {
    'T1':  Target('T1', '', 'Target 1', 'HAB1', 'PRE1', 'POST1', ''),
    'T2':  Target('T2', '', 'Target 2', 'HAB2', 'PRE2', 'POST2', ''),
}

# Restoration targets for the Southern Oregon Coast (Upmqua, Coquille, and Coos Rivers)

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
    'CO':  Target('CO', CO, 'Coho', 'sCO', 'PREPASS_CO', 'POSTPASS', 'Coho_salmon'),
    'CH':  Target('CH', CH, 'Chinook', 'sCH', 'PREPASS_CH', 'POSTPASS', 'Chinook_salmon'),
    'ST':  Target('ST', ST, 'Steelhead', 'sST', 'PREPASS_ST', 'POSTPASS', 'Steelhead'),
    'CT':  Target('CT', CT, 'Cutthroat', 'sCT', 'PREPASS_CT', 'POSTPASS', 'Cutthroat_Trout'),
    'CU':  Target('CU', CU, 'Chum', 'sCU', 'PREPASS_CU', 'POSTPASS', 'Chum'),
}

current_infrastructure_targets = {
    'FI': Target('FI', FI, 'Inund', 'sInundHab_Current', 'PREPASS_FISH', 'POSTPASS', 'InundHab_Current'),
    'AG': Target('AG', AG, 'Agric', 'sAgri_Current', 'PREPASS_AgrInf', 'POSTPASS', 'Agri_Current'),
    'RR': Target('RR', RR, 'Roads', 'sRoadRail_Current', 'PREPASS_AgrInf', 'POSTPASS', 'RoadRail_Current'),
    'BL': Target('BL', BL, 'Bldgs', 'sBuilding_Current', 'PREPASS_AgrInf', 'POSTPASS', 'Building_Current'),
    'PS': Target('PS', PS, 'Public', 'sPublicUse_Current', 'PREPASS_AgrInf', 'POSTPASS', 'PublicUse_Current'),
}

future_infrastructure_targets = {
    'FI': Target('FI', FI, 'Inund', 'sInundHab_Future', 'PREPASS_FISH', 'POSTPASS', 'InundHab_Future'),
    'AG': Target('AG', AG, 'Agric', 'sAgri_Future', 'PREPASS_AgrInf', 'POSTPASS', 'Agri_Future'),
    'RR': Target('RR', RR, 'Roads', 'sRoadRail_Future', 'PREPASS_AgrInf', 'POSTPASS', 'RoadRail_Future'),
    'BL': Target('BL', BL, 'Bldgs', 'sBuilding_Future', 'PREPASS_AgrInf', 'POSTPASS', 'Building_Future'),
    'PS': Target('PS', PS, 'Public', 'sPublicUse_Future', 'PREPASS_AgrInf', 'POSTPASS', 'PublicUse_Future'),
}

####################
#
# Unit tests
#
# Run the tests from the main project directory so pytest finds
# the test data:
#
#   $ pytest tidegates/targets.py
#

class TestProject:

    @staticmethod
    def test_TNC_columns():
        '''
        Make sure the column names in the Target objects are the same as
        the column names in the data file
        '''
        with open('static/workbook.csv') as f:
            cols = f.readline().strip().split(',')
        targets = make_targets(DataSet.TNC_OR)
        for s in ['Current', 'Future']:
            for t in targets[s].values():
                assert t.habitat in cols
                assert t.prepass in cols
                assert t.postpass in cols
                assert t.unscaled in cols

    @staticmethod
    def test_OPM_columns():
        with open('static/test_wb.csv') as f:
            cols = f.readline().strip().split(',')
        targets = make_targets(DataSet.OPM)
        for s in ['1','2']:
            name = 'T' + s
            assert name in targets
            t = targets[name]
            assert t.habitat in cols
            assert t.prepass in cols
            assert t.postpass in cols

