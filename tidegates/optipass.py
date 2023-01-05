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

import pandas as pd

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
    '''
    structs = BF.targets[climate]
    filtered = BF.data[BF.data.REGION.isin(regions)]
    of = filtered[['BARID','REGION','DSID']]
    header = ['ID', 'REG', 'DS']
    for t in targets:
        of = pd.concat([of, filtered[structs[t].habitat]], axis=1)
        header.append('HAB_'+t)
    for t in targets:
        of = pd.concat([of, filtered[structs[t].prepass]], axis=1)
        header.append('PRE_'+t)
    of = pd.concat([of, filtered['NPROJ'], filtered['COST']], axis=1)
    header += ['NPROJ','COST']
    for t in targets:
        of = pd.concat([of, filtered[structs[t].postpass]], axis=1)
        header.append('POST_'+t)
    of.columns = header
    return of

# OptiPass is a Windows-only app.  On macOS/Linux just print the name of the
# barrier file and commands that run OP (useful for debugging).  To see if
# we're running on Windows look for the uname attribute in the os module.

def run(
    barrier_file: str, 
    budget_max: int, 
    budget_delta: int
) -> list[str]:
    '''
    Generate and execute the shell commands that run OptiPass.
    '''
    template = r'.\bin\OptiPassMain.exe -f {bf} -o {of} -b {bl}'
    on_windows = getattr(os, 'uname', None) is None
    if not on_windows:
        print('barrier file written to', barrier_file)
    outputs = []
    for i in range(budget_max // budget_delta):
        outfile = f'optipass_{i+1}.txt'
        cmnd = template.format(
            bf = barrier_file,
            of = outfile,
            bl = budget_delta * (i+1)
        )
        if on_windows:
            print(cmnd)
            res = subprocess.run(cmnd, shell=True, capture_output=True)
            if res.returncode == 0:
                outputs.append(outfile)
        else:
            print(cmnd)
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
        _, path = tempfile.mkstemp(suffix='.txt',text=True)
        bf.to_csv(path, index=False, sep='\t', na_rep='NA')

        # Read the file, test its expected structure      
        tf = pd.read_csv(path, sep='\t')

        assert len(tf) == 10
        assert list(tf.columns) == ['ID','REG', 'DS', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'COST', 'POST_CO', 'POST_CH']
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
        _, path = tempfile.mkstemp(suffix='.txt',text=True)
        bf.to_csv(path, index=False, sep='\t', na_rep='NA')
        bmax = args.budget[0]
        bdelt = bmax // args.budget[1]
        run(path, bmax, bdelt)
    else:
        print(bf)
