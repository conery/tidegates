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

import pandas as pd

####################
#
# API used by web app
#

def generate_barrier_file(**kwargs):
    '''
    Create a barrier file that will be read by OptiPass.
    '''
    pass

def run(**kwargs):
    '''
    Generate and execute the shell commands that run OptiPass.
    '''
    pass

def parse_results(**kwargs):
    '''
    Parse the output files produced by OptiPass, collect results 
    in a Pandas dataframe.
    '''
    pass

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
    parser.add_argument('--region', metavar='R', required=True, nargs='+', help='one or more region names')
    parser.add_argument('--target', metavar='T', required=True, nargs='+', help='one or more restoration target IDs')
    parser.add_argument('--budget', metavar='N', nargs=2, default=(1000000, 10), help='maximum budget and number of increments')
    
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] == 'help'):
        print(parser.print_help())
        exit(0)

    return parser.parse_args()

if __name__ == '__main__':
    args = init_api()
    print('run optipass', args)
