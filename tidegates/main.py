import argparse
import panel as pn
import subprocess
import sys

from widgets import TideGates
from barriers import load_barriers, BF
from optipass import run_OP
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

    parser.add_argument('--action', metavar='A', choices=['run','parse','test'], help='operation to perform (run, parse, test)')
    parser.add_argument('--barriers', metavar='F', default='static/workbook.csv', help='CSV file with barrier data')
    parser.add_argument('--regions', metavar='R', default='all', nargs='+', help='one or more region names')
    parser.add_argument('--targets', metavar='T', nargs='+', default=['CO','FI'], help='one or more restoration targets')
    parser.add_argument('--budget', metavar='N', nargs=2, default=[5000,1000], help='max budget, budget delta')
    parser.add_argument('--climate', metavar='C', choices=['current','future'], default='current', help='climate scenario')

    return parser.parse_args()

def check_environment():
    '''
    We can't run OptiPass unless wine is installed
    '''
    res = subprocess.run(['which','wine'], capture_output=True)
    if len(res.stdout) == 0:
        print('wine needed to run OptiPass.exe')
        exit(1)

def make_app():
    template = pn.template.BootstrapTemplate(title='Tide Gate Optimization')
    tg = TideGates()
    template.sidebar.append(tg.map_pane)
    template.main.append(tg.main)
    return template

def start_app():
    pn.extension(sizing_mode = 'stretch_width')
    pn.config.css_files = ['static/tgo.css']
    pn.serve( 
        {'tidegates': make_app},
        port = 5006,
        admin = True,
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

if __name__ == '__main__':
    if len(sys.argv) == 1:
        Logging.setup('panel')
        start_app()
    else:
        args = init_cli()
        check_environment()
        Logging.setup('api')
        load_barriers(args.barriers)
        regions = BF.regions if args.regions == 'all' else args.regions
        targets = args.targets
        climate = args.climate.capitalize()
        budgets = parse_budget(args.budget)
        validate_options('region', regions, BF.regions)
        validate_options('target', targets, list(BF.target_map.values()))
        run_OP(regions, targets, climate, budgets, preview=(args.action=='test'))
