import argparse
from glob import glob
import re
import sys

import panel as pn

from tidegates.widgets import TideGates
from tidegates.targets import DataSet
from tidegates.project import Project
from tidegates.optipass import OP
from tidegates.messages import Logging

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
    """
    Use argparse to create the command line API.

    Returns:
        a Namespace object with values of the command line arguments. 
    """
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=desc,
        epilog=epi,
    )

    # NOTE:  no argument can be required -- it should be possible to run this script with no
    # command line arguments, which is how it's run in the Docker container when launching the
    # web app

    parser.add_argument('--action', metavar='A', choices=['generate', 'preview', 'run', 'parse', 'all', 'gui'], help='operation to perform')
    parser.add_argument('--project', metavar='F', default='static/workbook.csv', help='CSV file with barrier data')
    parser.add_argument('--regions', metavar='R', default='all', nargs='+', help='one or more region names')
    parser.add_argument('--targets', metavar='T', nargs='+', default=['CO','FI'], help='one or more restoration targets')
    parser.add_argument('--budget', metavar='N', nargs=2, default=[5000,1000], help='max budget, budget delta')
    parser.add_argument('--climate', metavar='C', choices=['current','future'], default='current', help='climate scenario')
    parser.add_argument('--output', metavar='F', help='base name of output files (optional)')
    parser.add_argument('--scaled', action='store_true', help='compute benefit using scaled amounts')

    return parser.parse_args()

def make_app():
    """
    Instantiate the top level widget.

    Returns:
        a TideGates object
    """
    return TideGates(
        title='Tide Gate Optimization', 
        sidebar_width=450
    )

def start_app():
    """
    Launch the Bokeh server.
    """
    pn.extension(design='native')
    pn.serve( 
        {'tidegates': make_app},
        port = 5006,
        admin = True,
        verbose = True,
        autoreload = True,
        websocket_origin= '*',
    )

def validate_options(
    name: str, 
    given: list[str], 
    expected: list[str],
):
    """
    Make sure values specified on the command line are valid for that option.
    Prints an error message and exits if an unknown value is specified.

    Example: check the names specified for the "region" option by making sure
    the values on the command line ("args.region") are in the list of valid
    names ("region_names").

        validate_options('region', args.regions, region_names)

    Args:
        name: the argument name
        given:  the strings typed by the user on the command line
        expected:  a list of acceptable values
    """
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
        op = OP(p,regions,targets,None,climate)

        match args.action:
            case 'generate':
                print(op.generate_input_frame())
            case 'preview' | 'run':
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
                op.make_roi_curves().show()
            case 'all':
                op.generate_input_frame()
                op.run(budgets, args.action=='preview')
                if op.outputs is not None:
                    op.collect_results(args.scaled)
                    print(op.table_view())
                    op.make_roi_curves().show()
            case 'gui':
                if not (args.budget and args.output):
                    print('gui action requires --output and --budget')
                    exit(1)
                app = make_app()
                app.title = 'Tide Gate Optimization [Integration Test]'
                app.optimize_button.disabled = True
                for r in regions:
                    for b in app.region_boxes.grid:
                        if b.name == r:
                            b.value = True
                m = app.bf.targets['Current']
                for t in targets:
                    s = m[t].long
                    for b in app.target_boxes.tabs[0].grid:
                        if b.name == s:
                            b.value = True
                op = OP(p,regions,targets,None,climate)
                op.budget_max, op.budget_delta = budgets
                op.input_frame = op.generate_input_frame()
                op.outputs = output_files(args.output)
                op.collect_results(False)
                app.add_output_pane(op)
                app.tabs.active = 2
                pn.extension(design='native')
                pn.serve(app, autoreload=True)

