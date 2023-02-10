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

import argparse
import sys
import os
import subprocess
from time import sleep

import pandas as pd
import numpy as np
import panel as pn

from barriers import load_barriers, BF

####################
#
# API used by web app
#

# Create a Pandas frame that has a subset of the columns from the main
# data frame that will be written to the barrier file.

def generate_barrier_file(
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
    barrier_file: str, 
    num_targets: int,
    budget_max: int, 
    budget_delta: int
) -> list[str]:
    '''
    Generate and execute the shell commands that run OptiPass.
    '''
    template = r'wine bin/OptiPassMain.exe -f {bf} -o {of} -b {bl}'
    outputs = []
    root, _ = os.path.splitext(barrier_file)
    for i in range(budget_max // budget_delta):
        outfile = f'{root}_{i+1}.txt'
        cmnd = template.format(
            bf = barrier_file,
            of = outfile,
            bl = budget_delta * (i+1)
        )
        if num_targets > 1:
            cmnd += ' -t {}'.format(num_targets)
        pn.state.log(cmnd)
        res = subprocess.run(cmnd, shell=True, capture_output=True)
        if res.returncode == 0:
            outputs.append(outfile)
        else:
            pn.state.log('OptiPass failed:')
            pn.state.log(res.stderr)
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
        bf = generate_barrier_file(climate='Current', regions=['Coos'], targets=['CO', 'CH'])

        # Write the frame to a CSV file
        _, path = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        bf.to_csv(path, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

        # Read the file, test its expected structure      
        tf = pd.read_csv(path, sep='\t')

        assert len(tf) == 10
        assert list(tf.columns) == ['ID','REG', 'FOCUS', 'DSID', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'ACTION', 'COST', 'POST_CO', 'POST_CH']
        assert tf.COST.sum() == 985000
        assert round(tf.HAB_CO.sum(), 3) ==  0.298

####################
#
# Command line API
#

desc = '''
Script to test and run OptiPass.
'''

epi = '''
Examples:

  $ python optipass.py ...
'''

def init_api():
    parser = argparse.ArgumentParser(description = desc, epilog=epi)
    parser.add_argument('--data', metavar='F', default='static/test_barriers.csv', help='CSV file with barrier data')
    parser.add_argument('--run', action='store_true', help='run OptiPass after creating barrier file')
    parser.add_argument('--climate', metavar='X', choices=['current','future'], default='current', help='climate scenario')
    parser.add_argument('--regions', metavar='R', required=True, nargs='+', help='one or more region names')
    parser.add_argument('--targets', metavar='T', required=True, nargs='+', help='one or more restoration target IDs')
    parser.add_argument('--budget', metavar='N', nargs=2, default=(1000000, 10), help='maximum budget and number of increments')
    
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == 'help'):
        print(parser.print_help())
        exit(0)

    return parser.parse_args()

if __name__ == '__main__':
    args = init_api()
    load_barriers(args.data)
    bf = generate_barrier_file(regions=args.regions, targets=args.targets)
    if args.run:
        _, path = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        bf.to_csv(path, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')
        bmax = args.budget[0]
        bdelt = bmax // args.budget[1]
        run(path, len(args.regions), bmax, bdelt)
    else:
        print(bf)
