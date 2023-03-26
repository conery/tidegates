#
# Interface to OptiPass.exe (command line version of OptiPass)
#
# An instance of the OP class encapsulates all the information
# related to a single optimization run.  The constructor, called
# from the GUI, is passed the options selected by the user (budget
# levels, restoration targets, etc).  Methods of the class set up
# and run an optimization based on these options:
#
#   OP.generate_input_frame
#       collect the columns from the main data file, save them in
#       a frame that has all the informtion that will be needed by OP
#
#   OP.run
#       runs the optimizer for each budget level requested by the
#       user, records the names of the data files generated
#
#   OP.collect_results
#       parse the output files, collect the relevant data in a frame
#       that is passed back to the calling function
#
# An OP object can also be instantiated by the command line API in
# main.py.  When run on macOS or Linux it can be used to test the 
# functions that creates the OP input file and parse the results.  
# When run on a Windows system it can also run OptiPass.
#

import os
import subprocess
from glob import glob
from math import prod

import pandas as pd
import numpy as np
import networkx as nx
import tempfile

from bokeh.plotting import figure, show
from bokeh.layouts import row, Spacer
from bokeh.models import NumeralTickFormatter

from messages import Logging
from project import Project
from targets import DataSet

class OP:

    def __init__(self, project: Project, regions: list[str], targets: list[str], climate: str):
        '''
        Instatiate a new OP object.
        * project is a Project object containing barrier data
        * regions is a list of unique names from the barrier file
        * targets is a list of 2-letter target IDs
        * climate is either 'Current' or 'Future'
        '''
        self.project = project
        self.regions = regions
        self.climate = climate
        structs = self.project.targets[climate] if climate else self.project.targets
        self.targets = [structs[t] for t in targets]
        self.input_frame = None
        self.outputs = None

    def generate_input_frame(self):
        '''
        Create a data frame that will be written in the format of a "barrier
        file" that will be read by OptiPass.  Save the frame as the
        input_frame attribute of the object.
        '''

        filtered = self.project.data[self.project.data.REGION.isin(self.regions)]
        filtered.index = list(range(len(filtered)))

        df = filtered[['BARID','REGION']]
        header = ['ID','REG']

        df = pd.concat([df, pd.Series(np.ones(len(filtered)), name='FOCUS', dtype=int)], axis=1)
        header.append('FOCUS')

        df = pd.concat([df, filtered['DSID']], axis=1)
        header.append('DSID')

        for t in self.targets:
            df = pd.concat([df, filtered[t.habitat]], axis=1, ignore_index=True)
            header.append('HAB_'+t.abbrev)

        for t in self.targets:
            df = pd.concat([df, filtered[t.prepass]], axis=1, ignore_index=True)
            header.append('PRE_'+t.abbrev)

        df = pd.concat([df, filtered['NPROJ']], axis=1, ignore_index=True)
        header.append('NPROJ')

        df = pd.concat([df, pd.Series(np.zeros(len(filtered)), name='ACTION', dtype=int)], axis=1)
        header.append('ACTION')

        df = pd.concat([df, filtered['COST']], axis=1, ignore_index=True)
        header += ['COST']

        for t in self.targets:
            df = pd.concat([df, filtered[t.postpass]], axis=1, ignore_index=True)
            header.append('POST_'+t.abbrev)

        df.columns = header
        self.input_frame = df
        return df

    # This version assumes the web app is running on a host that has wine installed
    # to run OptiPass (a Windows .exe file).

    def run(self, budgets: list[int], preview: bool, progress_hook = lambda: 0):
        '''
        Generate and execute the shell commands that run OptiPass.  If the shell
        environment includes a variable named WINEARCH it means the script is
        running on Linux, and we need to use Wine, otherwise build a command that
        will run on Windows.
        '''
        app = 'wine bin/OptiPassMain.exe' if os.environ.get('WINEARCH') else 'bin\\OptiPassMain.exe'
        template = app + ' -f {bf} -o {of} -b {n}'

        df = self.generate_input_frame()
        _, barrier_file = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        df.to_csv(barrier_file, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

        self.budget_max, self.budget_delta = budgets
        num_budgets = self.budget_max // self.budget_delta
        outputs = []
        root, _ = os.path.splitext(barrier_file)
        for i in range(num_budgets + 1):
            outfile = f'{root}_{i+1}.txt'
            budget = self.budget_delta * i
            # cmnd = f'wine bin/OptiPassMain.exe -f {barrier_file} -o {outfile} -b {budget}'
            cmnd = template.format(bf=barrier_file, of=outfile, n=budget)
            if (num_targets := len(self.targets)) > 1:
                cmnd += ' -t {}'.format(num_targets)
                cmnd += ' -w' + ' 1.0' * num_targets
            Logging.log(cmnd)
            if not preview:
                res = subprocess.run(cmnd, shell=True, capture_output=True)
            if preview or (res.returncode == 0):
                outputs.append(outfile)
                progress_hook()
            else:
                Logging.log('OptiPass failed:')
                Logging.log(res.stderr)
        self.outputs = outputs

    def collect_results(self, scaled=False):
        '''
        Parse the output files produced by OptiPass
        '''
        df = self.input_frame
        G = nx.from_pandas_edgelist(
            df[df.DSID.notnull()], 
            source='ID', 
            target='DSID', 
            create_using=nx.DiGraph
        )
        for x in df[df.DSID.isnull()].ID:
            G.add_node(x)
        self.paths = { n: self._path_from(n,G) for n in G.nodes }

        # costs = { self.project.data.BARID[i]: self.project.data.COST[i] for i in self.project.data.index }

        cols = { x: [] for x in ['budget', 'weights', 'habitat', 'gates']}
        for fn in self.outputs:
            self._parse_op_output(fn, cols)
        self.weights = cols['weights'][0]           # should all be the same

        del cols['weights']
        self.summary = pd.DataFrame(cols)
        
        dct = {}
        for i in range(len(self.summary)):
            b = int(self.summary.budget[i])
            dct[b] = [ 1 if g in self.summary.gates[i] else 0 for g in self.input_frame.ID]
        self.matrix = pd.DataFrame(dct, index=self.input_frame.ID)
        self.matrix['count'] = self.matrix.sum(axis=1)
        self.potential_habitat(self.targets, scaled)


    def _path_from(self, x, graph):
        '''
        Return a list of nodes in the path from `x` to a downstream barrier that
        has no descendants.
        '''
        return [x] + [child for _, child in nx.dfs_edges(graph,x)]

    def _parse_op_output(self, fn, dct):
        '''
        Parse an output file, appending results to the lists.  We need to handle
        two different format, depending on whether there was one target or more
        than one.

        This version ignores the STATUS and OPTGAP lines.
        '''

        def parse_header_line(line, tag):
            tokens = line.strip().split()
            if not tokens[0].startswith(tag):
                return None
            return tokens[1]

        with open(fn) as f:
            amount = parse_header_line(f.readline(), 'BUDGET')
            dct['budget'].append(float(amount))
            f.readline()                        # skip STATUS
            f.readline()                        # skip OPTGAP
            line = f.readline()
            if line.startswith('PTNL'):
                dct['weights'].append([1.0])
                hab = parse_header_line(line, 'PTNL_HABITAT')
                dct['habitat'].append(float(hab))
                f.readline()                    # skip NETGAIN
            else:
                lst = []
                while w := parse_header_line(f.readline(), 'TARGET'):
                    lst.append(float(w))
                dct['weights'].append(lst)
                while line := f.readline():      # skip the individual habitat lines
                    if line.startswith('WT_PTNL_HAB'):
                        break
                hab = parse_header_line(line, 'WT_PTNL_HAB')
                dct['habitat'].append(float(hab))
                f.readline()                    # skip WT_NETGAIN
            f.readline()                        # skip blank line
            f.readline()                        # skip header
            lst = []
            while line := f.readline():
                name, action = line.strip().split()
                if action == '1':
                    lst.append(name)
            dct['gates'].append(lst)

    def potential_habitat(self, tlist, scaled):
        '''
        Compute the potential habitat available before and after restoration, using
        the original unscaled habitat values.
        '''
        filtered = self.project.data[self.project.data.REGION.isin(self.regions)].fillna(0)
        filtered.index = filtered.BARID
        wph = np.zeros(len(self.summary))
        for i in range(len(tlist)):
            t = self.targets[i]
            cp = self._ah(t, filtered, scaled)
            wph += (self.weights[i] * cp)
            col = pd.DataFrame({t.abbrev: cp})
            self.summary = pd.concat([self.summary, col], axis=1)
            if not scaled:
                gain = self._gain(t, filtered)
                self.matrix = pd.concat([self.matrix, filtered[t.unscaled], gain], axis=1)

        # If scaled is True add the wph column so we can compare with OP values
        if scaled:
            self.summary = pd.concat([self.summary, pd.DataFrame({'wph': wph})], axis = 1)
        self.summary['netgain'] = self.summary.habitat - self.summary.habitat[0]
        return self.summary
    
    # Private method: compute the available habitat for a target, in the form of
    # a vector of habitat values for each budget level

    def _ah(self, target, data, scaled):
        budgets = self.summary.budget
        m = self.matrix
        res = np.zeros(len(budgets))
        for i in range(len(res)):
            action = m.iloc[:,i]
            pvec = data[target.postpass].where(action == 1, data[target.prepass])
            habitat = data[target.habitat if scaled else target.unscaled]
            res[i] = sum(prod(pvec[x] for x in self.paths[b]) * habitat[b] for b in m.index)
        return res
    
    def _gain(self, target, data):
        col = (data[target.postpass] - data[target.prepass]) * data[target.unscaled]
        return col.to_frame(name=f'GAIN_{target.abbrev}')
    
    def table_view(self, test=False):
        '''
        Create a table that will be displayed by the GUI
        '''
        filtered = self.project.data[self.project.data.REGION.isin(self.regions)]
        filtered = filtered.set_index('BARID')

        if test:
            info_cols = other_cols = { }
        else:
            info_cols = {
                'REGION': 'Region',
                'BarrierType': 'Type',
                'DSID': 'DSID',
                'COST': 'Cost',
            }

            other_cols = {
                'PrimaryTG': 'Primary',
                'DominantTG': 'Dominant',
                'POINT_X': 'Longitude',
                'POINT_Y': 'Latitude',
            }

        budget_cols = OP.format_budgets([c for c in self.matrix.columns if isinstance(c,int) and c > 0])

        df = pd.concat([
            filtered[info_cols.keys()].rename(columns=info_cols),
            self.matrix.rename(columns=budget_cols),
            filtered[other_cols.keys()].rename(columns=other_cols),
        ], axis=1)

        dct = { t.unscaled: t.short+'_hab' for t in self.targets }
        dct |= { f'GAIN_{t.abbrev}': t.short+'_gain' for t in self.targets }
        df = df.rename(columns=dct)

        del df[0]
        df = df[df['count'] > 0].sort_values(by='count', ascending=False).fillna('-')
        df = df.rename(columns={'count': 'Count'})
        df = df.reset_index(names=['ID'])

        # df.columns = pd.MultiIndex.from_tuples(df.columns)
        return df

    @staticmethod
    def format_budgets(cols):
        fmt = {
            'thou':  (1000, 'K'),
            'mil':   (1000000, 'M'),
        }
        res = { }
        for n in cols:
            divisor, suffix = fmt['mil'] if n >= 1000000 else fmt['thou']
            s = '${:}'.format(n/divisor)
            if s.endswith('.0'):
                s = s[:-2]
            res[n] = s+suffix
        return res
    
    def roi_curves(self):
        H = 400
        W = 400
        LW = 2
        D = 10
        figures = []
        for t in self.targets:
            f = figure(
                title=t.long, 
                x_axis_label='Budget', 
                y_axis_label='Post-Restoration Habitat',
                width=W,
                height=H,                
                )
            f.line(self.summary.budget, self.summary[t.abbrev], line_width=LW)
            f.circle(self.summary.budget, self.summary[t.abbrev], fill_color='white', size=D)
            f.xaxis.formatter = NumeralTickFormatter(format='$0a')
            f.toolbar_location = None
            figures.append(f)
            figures.append(Spacer(width=50))
        f = figure(
            title='Weighted Potential Habitat', 
            x_axis_label='Budget', 
            y_axis_label='Net Gain',
            width=W,
            height=H,
            )
        f.line(self.summary.budget, self.summary.netgain, line_width=LW)
        f.circle(self.summary.budget, self.summary.netgain, fill_color='white', size=D)
        f.xaxis.formatter = NumeralTickFormatter(format='$0a')
        f.toolbar_location = None
        figures.append(f)
        return row(*figures)

####################
#
# Tests
#

import pytest

class TestOP:

    @staticmethod
    def test_instantiate_object():
        '''
        Test the OP constructor.
        '''
        p = Project('static/workbook.csv', DataSet.TNC_OR)
        op = OP(p, ['Coos'], ['CO','CH'], 'Current')
        assert op.project == p
        assert op.regions == ['Coos']
        assert op.climate == 'Current'
        assert len(op.targets) == 2
        t = op.targets[0]
        assert t.abbrev == 'CO'
        assert t.short == 'Coho'
        assert t.long == 'Fish habitat: Coho streams'

    @staticmethod
    def test_generate_frame():
        '''
        Test the structure of a frame that will be printed as a
        'barrier file' for input to OptiPass
        '''

        p = Project('static/workbook.csv', DataSet.TNC_OR)
        op = OP(p, ['Coos'], ['CO','CH'], 'Current')
        op.generate_input_frame()
        tf = op.input_frame

        assert list(tf.columns) == ['ID','REG', 'FOCUS', 'DSID', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'ACTION', 'COST', 'POST_CO', 'POST_CH']

    # NOTE:  the OPM project does not have habitat in unscaled ("target") unita
    # so the calls to collect_results in these tests need to specify scaled = True

    @staticmethod
    def test_example_1():
        '''
        Test the OPResults class by collecting results for Example 1 from the 
        OptiPass User Manual.
        '''
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1'], None)
        op.input_frame = pd.read_csv('static/Example_1/Example1.txt', sep='\t')
        op.outputs = sorted(glob('static/Example_1/example_*.txt'))
        op.collect_results(scaled=True)

        assert len(op.targets) == 1
        assert op.targets[0].abbrev == 'T1'
        assert len(op.weights) == 1 and round(op.weights[0]) == 1

        assert type(op.summary) == pd.DataFrame
        assert len(op.summary) == 6
        assert round(op.summary.budget.sum()) == 1500
        assert round(op.summary.habitat.sum(),2) == 23.30

        budget_cols = [col for col in op.matrix.columns if isinstance(col,int)]
        assert budget_cols == list(op.summary.budget)

        # these comprehensions make lists of budgets where a specified gate was selected
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['A',b]] == [400,500]
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['D',b]] == [ ]
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['E',b]] == [100,300]

        assert op.paths['E'] == ['E','D','A']
        assert op.paths['A'] == ['A']

    @staticmethod
    def test_example_4():
        '''
        Same as test_example_1, but using Example 4, which has two restoration targets.
        '''
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1','T2'], None)
        op.input_frame = pd.read_csv('static/Example_4/Example4.txt', sep='\t')
        op.outputs = sorted(glob('static/Example_4/example_*.txt'))
        op.collect_results(scaled=True)

        assert len(op.targets) == 2
        assert op.targets[0].abbrev == 'T1' and op.targets[1].abbrev == 'T2'
        assert len(op.weights) == 2 and round(sum(op.weights)) == 4

        assert type(op.summary) == pd.DataFrame
        assert len(op.summary) == 6
        assert round(op.summary.budget.sum()) == 1500
        assert round(op.summary.habitat.sum(),2) == 95.21

        # using two targets does not change the gate selections
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['A',b]] == [400,500]
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['D',b]] == [ ]
        assert [b for b in op.matrix.columns if b != 'count' and op.matrix.loc['E',b]] == [100,300]

    @staticmethod
    def test_potential_habitat_1():
        '''
        Test the method that computes potential habitat, using the results 
        genearated for Example 1 in the OptiPass manual.
        '''
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1'], None)
        op.input_frame = pd.read_csv('static/Example_1/Example1.txt', sep='\t')
        op.outputs = sorted(glob('static/Example_1/example_*.txt'))
        op.collect_results(scaled=True)

        m = op.summary
        assert len(m) == 6
        assert 'T1' in m.columns and 'wph' in m.columns
        assert round(m.wph[0],3) == 1.238
        assert round(m.wph[5],3) == 8.520

    @staticmethod
    def test_potential_habitat_4():
        '''
        Same as test_potential_habitat_1, but using Example 4, with two restoration targets
        '''
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1','T2'], None)
        op.input_frame = pd.read_csv('static/Example_4/Example4.txt', sep='\t')
        op.outputs = sorted(glob('static/Example_4/example_*.txt'))
        op.collect_results(scaled=True)

        m = op.summary
        assert len(m) == 6
        assert 'T1' in m.columns and 'T2' in m.columns and 'wph' in m.columns
        assert round(m.wph[0],3) == 5.491
        assert round(m.wph[4],3) == 21.084    # the value shown in the OP manual

    @staticmethod
    def test_budget_formats():
        '''
        Test the function that generates budget labels.
        '''
        assert list(OP.format_budgets([n*1000000 for n in range(1,6)]).values()) == ['$1M', '$2M', '$3M', '$4M', '$5M']
        assert list(OP.format_budgets([n*100000 for n in range(1,6)]).values()) == ['$100K', '$200K', '$300K', '$400K', '$500K']
        assert list(OP.format_budgets([n*500000 for n in range(1,6)]).values()) == ['$500K', '$1M', '$1.5M', '$2M', '$2.5M']
