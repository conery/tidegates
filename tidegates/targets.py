# 
# Restoration Targets 
# 
# This file is basically a configuration file, a place to define the names
# and attribures of restoration targets specific to a set of regions.
#
# A Target object has two kinds of information about a restoration target,
# names that are displayed in the GUI and appear in data tables and plots,
# and column names that identify which columns in the main data file are
# associated with the target.
#
# An application can call make_targets to get a dictionary that associates
# target IDs with Target objects.
#

from collections import namedtuple

# FIXME
# convert Target to a class so field names are exposed to documentation
# generator

Target = namedtuple('Target', ['abbrev', 'long', 'short', 'habitat', 'prepass', 'postpass', 'unscaled'])

# Make the targets for the Southern Oregon Coast 

def make_targets():
    '''
    Create dictionaries with target records for each climate scenario,
    and a dictionary that maps long descriptions to target IDs
    '''
    current = dict(fish_targets)
    current |= current_infrastructure_targets
    future = dict(fish_targets)
    future |= future_infrastructure_targets
    return {
        'Current': current,
        'Future': future,
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
