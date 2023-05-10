import argparse
from glob import glob
import os
import re
import subprocess
import sys

import panel as pn
from bokeh.plotting import show

from widgets import TideGates
from targets import DataSet
from project import Project
from optipass import OP
from messages import Logging

desc = '''
User interface for the Tide Gates Optimization app.  If no arguments or options
are specified the GUI is started.  

To run the optimizer specify "--action A" where A is an operation to perform,
based on the values of the remaining options.
  * 'test' will print the shell commands that will be passed to the optimizer,
    use it to make sure the options are parsed as expected
  * 'run' will run the optimizer using the parsed options
  * 'parse F' will parse results from a previous run; use it to test the parser,
    using data in files in th temp folder that have names starting with F
'''

epi = '''
The --region argument is optional.  If used, specify one or more reqion names 
separated by spaces.  If it's not specified all regions are used.

If no name is specified with --output a random base name will be generated for
each run.  

Example:

    $ python3 tidegates/main.py --action run --region coos coquille --target CO CH --budget 250 50
    
        Uses barriers in the Coos and Coquille regions, targets CO (coho salmon) and 
        CH (chinook salmon), and five budget values from $50K to $250K.
'''

def init_cli():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=desc,
        epilog=epi,
    )

    # NOTE:  no argument can be required -- it should be possible to run this script with no
    # command line arguments, which is how it's run in the Docker container when launching the
    # web app

    parser.add_argument('--action', metavar='A', choices=['generate', 'preview', 'run', 'parse', 'all'], help='operation to perform')
    parser.add_argument('--project', metavar='F', default='static/workbook.csv', help='CSV file with barrier data')
    parser.add_argument('--regions', metavar='R', default='all', nargs='+', help='one or more region names')
    parser.add_argument('--targets', metavar='T', nargs='+', default=['CO','FI'], help='one or more restoration targets')
    parser.add_argument('--budget', metavar='N', nargs=2, default=[5000,1000], help='max budget, budget delta')
    parser.add_argument('--climate', metavar='C', choices=['current','future'], default='current', help='climate scenario')
    parser.add_argument('--output', metavar='F', help='base name of output files (optional)')
    parser.add_argument('--scaled', action='store_true', help='compute benefit using scaled amounts')

    return parser.parse_args()

def check_environment(action):
    '''
    We can't run OptiPass unless wine is installed
    '''
    if action == 'run':
        res = subprocess.run(['which','wine'], capture_output=True)
        if len(res.stdout) == 0:
            print('wine needed to run OptiPass.exe')
            exit(1)

def make_app():
    template = pn.template.BootstrapTemplate(title='Tide Gate Optimization', sidebar_width=425)
    tg = TideGates()
    template.sidebar.append(tg.map_pane)
    template.main.append(tg.main)
    if not os.environ.get('WINEARCH'):
        print('TBD: set region, budget, target')
    return template

def start_app():
    # pn.extension(sizing_mode = 'stretch_width')
    pn.config.css_files = ['static/tgo.css']
    pn.serve( 
        {'tidegates': make_app},
        port = 5006,
        admin = True,
        verbose = True,
        autoreload = True,
        websocket_origin= '*',
    )

def validate_options(name, given, expected):
    if not all(x in expected for x in given):
        print(f'unknown {name} not in {expected}')
        exit(1)

def parse_budget(budgets):
    try:
        if len(budgets) != 2:
            raise ValueError('--budget requires two arguments')
        bmax = int(budgets[0])
        bdelta = int(budgets[1])
    except Exception as err:
        print('budget max and delta must be integers')
        print(err)
        exit(1)
    return [bmax,bdelta]

def output_files(pattern):

    def number_part(fn):
        return int(re.search(r'_(\d+)\.txt$', fn).group(1))

    outputs = glob(f'tmp/{args.output}_*.txt')
    return sorted(outputs, key=number_part)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        Logging.setup('panel')
        start_app()
    else:
        args = init_cli()
        Logging.setup('api')

        p = Project(args.project, DataSet.TNC_OR)
        regions = p.regions if args.regions == 'all' else args.regions
        validate_options('region', regions, p.regions)

        targets = args.targets
        validate_options('target', targets, list(p.target_map.values()))

        climate = args.climate.capitalize()
        budgets = parse_budget(args.budget)
        op = OP(p,regions,targets,climate)

        match args.action:
            case 'generate':
                print(op.generate_input_frame())
            case 'preview' | 'run':
                check_environment(args.action)
                op.generate_input_frame()
                op.run(budgets, args.action=='preview')
            case 'parse':
                if not args.output:
                    print('--output required with --action parse')
                    exit(1)
                op.budget_max, op.budget_delta = budgets
                op.input_frame = op.generate_input_frame()
                op.outputs = output_files(args.output)
                op.collect_results(args.scaled)
                print(op.table_view())
                show(op.roi_curves())
            case 'all':
                op.generate_input_frame()
                op.run(budgets, args.action=='preview')
                op.collect_results(args.scaled)
                print(op.table_view())
                show(op.roi_curves())
