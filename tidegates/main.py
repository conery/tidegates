import argparse
import panel as pn
import sys

from widgets import TideGates
from barriers import load_barriers, BF
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

    $ python3 tidegates/main.py --action run --region coos coquille --target CO CH --budget 250 5
    
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
    parser.add_argument('--region', metavar='R', default='all', nargs='+', help='one or more region names')
    parser.add_argument('--target', metavar='T', nargs='+', default=['CH','CO'], help='one or more restoration targets')
    parser.add_argument('--budget', metavar='N', nargs=2, default=[5000,1000], help='max budget, number of budgets')
    parser.add_argument('--climate', metavar='C', choices=['current','future'], default='current', help='climate scenario')

    return parser.parse_args()

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

def parse_budget(bmax, bcount):
    try:
        bmax = int(bmax)
        bcount = int(bcount)
    except Exception as err:
        print('budget max and count must be integers')
        print(err)
        exit(1)
    return list(range(bcount, bmax+bcount, bcount))

if __name__ == '__main__':
    if len(sys.argv) == 1:
        Logging.setup('panel')
        start_app()
    else:
        args = init_cli()
        Logging.setup('api')
        load_barriers(args.barriers)
        if args.region == 'all':
            args.region = BF.regions
        else:
            validate_options('region', args.region, BF.regions)
        validate_options('target', args.target, list(BF.target_map.values()))
        args.budget = parse_budget(*args.budget)
        Logging.log('region', args.region)
        Logging.log('target', args.target)
        Logging.log('budget', args.budget)
        Logging.log('climate', args.climate)

