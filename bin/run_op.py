#! /usr/bin/env python3

# Launch OptiPass on the remote service, print the returned results.
#
# Usage:
#    $ run_op.py fn
# where fn is the name of the file to input to the optimizer.

import os
import sys
import requests

if len(sys.argv) < 2:
    print(f'Usage: {sys.argv[0]} filename')
    exit(1)

fn = sys.argv[1]

if not os.path.exists(fn):
    print(f'No such file: {fn}')
    exit(1)

with open(fn) as f:
    barriers = f.read()

# URL = 'https://tnc-tidegates-op.azurewebsites.net/api/tidegatesop'
# URL = 'https://tnc-optipass.azurewebsites.net/api/OptiPass'
URL = 'https://tnc-run-optipass.azurewebsites.net/api/OptiPass'

r = requests.post(URL, params = {'name': 'John'}, json = {'barriers': barriers})

if (r.status_code == requests.codes.ok):
    print(r.text)
else:
    print(f'request failed, code = {r.status_code}')
    print(r.reason)
