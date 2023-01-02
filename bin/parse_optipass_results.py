#! /usr/bin/env python3

# This script is designed to be run by the web app API.  There is only one
# command line argument, the name of the text file produced by OptiPass.

# All outputs are written to stdout so they can be captured by the API.

# Version 0.1 -- test the connection between the web app and this script,
# uses a data file that has summarized OptiPass output (instead of the actual
# raw outputs)

import os
import sys

def parse_budget_line(s):
    return [float(x) for x in s.strip().split('\t')[1:]]

def skip_to_next_section(f):
    s = f.readline().strip()
    while len(s) > 0:
        s = f.readline().strip()
    s = f.readline().strip()
    return s
    
def parse_targets(f):
    res = []
    line = f.readline().strip()
    while len(line) > 0:
        target, *benefits = line.split('\t')
        lst = [target]
        lst += benefits
        res.append(lst)
        line = f.readline().strip()
    return res

def parse_table(f):
    tbl = []
    line = f.readline().strip()
    while len(line) > 0:
        tbl.append(line.split('\t'))
        line = f.readline().strip()
    return tbl

def print_line(label, contents):
    s = ','.join([str(x) for x in contents])
    print(f'{label},{s}')

if len(sys.argv) < 2:
    print(f'{sys.argv[0]}: missing file name', file=sys.stderr)
    exit(1)

fn = sys.argv[1]
if not os.path.exists(fn):
    printf('{sys.argv[0]}: no such file: {fn}', file=sys.stderr)
    exit(1)

with open(fn) as f:
    line = f.readline()
    print_line('x',parse_budget_line(line))

    skip_to_next_section(f)
    for lst in parse_targets(f):
        print_line('y',lst)

    line = skip_to_next_section(f)
    print_line('h', line.strip().split('\t'))
    for lst in parse_table(f):
        print_line('t',lst)

