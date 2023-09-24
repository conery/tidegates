#! /usr/bin/env python3

# Scan a CSV file, look for anomalies:
#    look for required header names
#    if a name appears in the DSID column make sure it's also in BARID
#    NPROJ is 0 or 1
#    COST is an int
#    POINT_X and POINT_Y are floats
#    make sure NPROJ is 0 if PrimaryTG is not 1
#    make sure NPROJ is 0 if COST is 0

# TODO  add argument parser
# TODO  write sanitized file to stdout
# TODO  option to print stats (number of gates in each region, costs, ...)

import csv
import os
import re
import sys

if len(sys.argv) < 2:
    print(f'Usage: {sys.argv[0]} filename')
    exit(1)

fn = sys.argv[1]

if not os.path.exists(fn):
    print(f'No such file: {fn}')
    exit(1)

with open(fn) as f:
    reader = csv.DictReader(f)
    errors = [ ]

    for col in ['BARID', 'DSID', 'NPROJ', 'COST', 'POINT_X', 'POINT_Y']:
        if col not in reader.fieldnames:
            errors.append(f'Missing column: {col}')
    
    if errors:
        for e in errors:
            print(e)
        exit(1)

    barid = set()
    dsid = set()

    for rec in reader:
        if len(rec['BARID']) == 0:
            errors.append(f'Line {reader.line_num}: Missing barrier ID')
        else:
            barid.add(rec['BARID'])

        if len(rec['DSID']) == 0:
            errors.append(f'Line {reader.line_num}: Empty DSID')
        elif rec['DSID'] != 'NA':
            dsid.add(rec['DSID'])
        
        if rec['NPROJ'] not in ['0', '1']:
            errors.append(f'Line {reader.line_num}: NPROJ not 0 or 1')

        if not re.fullmatch(r'\d+(\.\d+)?', rec['COST']):
            errors.append(f'Line {reader.line_num}: COST not a number')

        for col in ['POINT_X','POINT_Y']:
            if not re.match(r'-?\d+\.\d+', rec[col]):
                errors.append(f'Line {reader.line_num}: {col} not a float')

        if rec['PrimaryTG'] == 0 and rec['NPROJ'] != 0:
            errors.append(f'Line {reader.line_num}: NPROJ not 0 for non-primary gate')
        
        if rec['COST'] == 0 and rec['NPROJ'] != 0:
            errors.append(f'Line {reader.line_num}: NPROJ not 0 when cost is $0')

    if s := dsid - barid:
        errors.append(f'Downstream IDs not in BARID column: {s}')

    for msg in errors:
        print(msg)

