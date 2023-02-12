#
# Interface to OptiPass (command line version)
#
# This module has functions that create the input file read by OptiPass
# (a "barrier file"), run OptiPass, and collect the outputs from OptiPass
# into a Pandas dataframe.
#
# The module also has its own command line API.  When run on macOS / Linux
# it can be used to test the function that creates the barrier file.  When
# run on a Windows system it can also run OptiPass.
#

import os
import subprocess

import pandas as pd
import numpy as np

from barriers import load_barriers, BF
from messages import Logging

####################
#
# API used by web app
#

# Create a Pandas frame that has a subset of the columns from the main
# data frame that will be written to the barrier file.

def generate_barrier_frame(
    regions: list[str],
    targets: list[str],
    climate: str = 'Current',
) -> pd.DataFrame:
    '''
    Create a barrier file that will be read by OptiPass.  Assumes the
    BF struct in the barriers module has been initialized.

    The frame has a new column named FOCUS, set to 1 in every row.  This
    code uses the POSTPASS column as the source of 1s.
    '''
    structs = BF.targets[climate]

    filtered = BF.data[BF.data.REGION.isin(regions)]
    filtered.index = list(range(len(filtered)))

    of = filtered[['BARID','REGION']]
    header = ['ID','REG']

    of = pd.concat([of, pd.Series(np.ones(len(filtered)), name='FOCUS', dtype=int)], axis=1)
    header.append('FOCUS')

    of = pd.concat([of, filtered['DSID']], axis=1)
    header.append('DSID')

    for t in targets:
        of = pd.concat([of, filtered[structs[t].habitat]], axis=1, ignore_index=True)
        header.append('HAB_'+t)

    for t in targets:
        of = pd.concat([of, filtered[structs[t].prepass]], axis=1, ignore_index=True)
        header.append('PRE_'+t)

    of = pd.concat([of, filtered['NPROJ']], axis=1, ignore_index=True)
    header.append('NPROJ')

    of = pd.concat([of, pd.Series(np.zeros(len(filtered)), name='ACTION', dtype=int)], axis=1)
    header.append('ACTION')

    of = pd.concat([of, filtered['COST']], axis=1, ignore_index=True)
    header += ['COST']

    for t in targets:
        of = pd.concat([of, filtered[structs[t].postpass]], axis=1, ignore_index=True)
        header.append('POST_'+t)

    of.columns = header
    return of

# This version assumes the web app is running on a host that has wine installed
# to run OptiPass (a Windows .exe file).

def run_OP(
    regions: list[str],
    targets: list[str],
    climate: str,
    budgets: list[int],
    preview: bool = False,
) -> list[str]:
    '''
    Generate and execute the shell commands that run OptiPass.
    '''
    bf = generate_barrier_frame(regions=regions, targets=targets, climate=climate)
    _, barrier_file = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
    bf.to_csv(barrier_file, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

    budget_max, budget_delta = budgets
    outputs = []
    root, _ = os.path.splitext(barrier_file)
    for i in range(budget_max // budget_delta):
        outfile = f'{root}_{i+1}.txt'
        budget = budget_delta * (i+1)
        cmnd = f'wine bin/OptiPassMain.exe -f {barrier_file} -o {outfile} -b {budget}'
        if num_targets := len(targets):
            cmnd += ' -t {}'.format(num_targets)
            cmnd += ' -w' + ' 1.0' * num_targets
        Logging.log(cmnd)
        if not preview:
            res = subprocess.run(cmnd, shell=True, capture_output=True)
        if preview or (res.returncode == 0):
            outputs.append(outfile)
        else:
            Logging.log('OptiPass failed:')
            Logging.log(res.stderr)
    return outputs

def parse_results(**kwargs):
    '''
    Parse the output files produced by OptiPass, collect results 
    in a Pandas dataframe.
    '''
    pass

####################
#
# Tests
#

import pytest
import tempfile

class TestOP:

    @staticmethod
    def test_generate_file():
        '''
        Write a barrier file, test its structure
        '''

        # Create barrier descriptions from the test data
        load_barriers('static/test_barriers.csv')
        bf = generate_barrier_frame(climate='Current', regions=['Coos'], targets=['CO', 'CH'])

        # Write the frame to a CSV file
        _, path = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        bf.to_csv(path, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

        # Read the file, test its expected structure      
        tf = pd.read_csv(path, sep='\t')

        assert len(tf) == 10
        assert list(tf.columns) == ['ID','REG', 'FOCUS', 'DSID', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'ACTION', 'COST', 'POST_CO', 'POST_CH']
        assert tf.COST.sum() == 985000
        assert round(tf.HAB_CO.sum(), 3) ==  0.298
