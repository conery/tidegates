
import platform
import os
import subprocess
from glob import glob
from math import prod

import pandas as pd
import param
import numpy as np
import panel as pn
import networkx as nx
import tempfile

from bokeh.plotting import figure
from bokeh.models import NumeralTickFormatter, HoverTool, Title

import matplotlib.pyplot as plt

from .messages import Logging
from .project import Project
from .targets import DataSet

class OP:
    """
    Interface to OptiPass.exe (the command line version of OptiPass)

    An instance of the OP class encapsulates all the information
    related to a single optimization run.  The constructor, called
    from the GUI, is passed the options selected by the user (budget
    levels, restoration targets, etc).  Methods of the class set up
    and run an optimization based on these options:

    An OP object can also be instantiated by the command line API in
    main.py.  When run on macOS or Linux it can be used to test the 
    functions that creates the OP input file and parse the results.  
    When run on a Windows system it can also run OptiPass.
    """

    def __init__(self, project: Project, regions: list[str], targets: list[str], weights: list[str], climate: str):
        '''
        Instantiate a new OP object.

        Arguments:
          project: a Project object containing barrier file
          regions: a list of region names from the barrier file
          targets: a list of 2-letter target IDs
          weights: optional list of integer weights for each target
          climate: either 'Current' or 'Future'
        '''
        self.project = project
        self.regions = regions
        if weights:
            self.weights = [int(s) for s in weights]
            self.weighted = True
        else:
            self.weights = [1] * len(targets)
            self.weighted = False
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
            df = pd.concat([df, filtered[t.habitat]], axis=1)
            header.append('HAB_'+t.abbrev)

        for t in self.targets:
            df = pd.concat([df, filtered[t.prepass]], axis=1)
            header.append('PRE_'+t.abbrev)

        df = pd.concat([df, filtered['NPROJ']], axis=1)
        header.append('NPROJ')

        df = pd.concat([df, pd.Series(np.zeros(len(filtered)), name='ACTION', dtype=int)], axis=1)
        header.append('ACTION')

        df = pd.concat([df, filtered['COST']], axis=1)
        header += ['COST']

        for t in self.targets:
            df = pd.concat([df, filtered[t.postpass]], axis=1)
            header.append('POST_'+t.abbrev)

        df.columns = header
        self.input_frame = df

        return df

    # def run(self, budgets: list[int], preview: bool, progress_hook = lambda: 0):
    def run(self, budgets: list[int], preview: bool):
        '''
        Generate and execute the shell commands that run OptiPass.  If the shell
        environment includes a variable named WINEARCH it means the script is
        running on Linux, and we need to use Wine, otherwise build a command that
        will run on Windows.

        The first time OptiPass is run it will be given a budget of $0 to establish
        the current passage levels.  It's then run once more at each level in the
        budgets list.

        Each time OptiPass is run it is passed the same input file, but it will
        write outputs to a separate file that includes the budget level in the file name.
        The list of output file names is saved in an instance variable.

        Arguments:
          budgets:  a list of budget values (dollar amounts)
          preview:  if True, print shell commands but don't execute them
        '''
        if platform.system() == 'Windows':
            app = 'bin\\OptiPassMain.exe'
        elif platform.system() == 'Linux' and os.environ.get('WINEARCH'):
            app = 'wine bin/OptiPassMain.exe'
        else:
            Logging.log(f'{platform.system()} not configured to run WINE')
            self.outputs = None
            return
        
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
            cmnd = template.format(bf=barrier_file, of=outfile, n=budget)
            if (num_targets := len(self.targets)) > 1:
                cmnd += ' -t {}'.format(num_targets)
                cmnd += ' -w ' + ', '.join([str(n) for n in self.weights])
            Logging.log(cmnd)
            print(cmnd)
            if not preview:
                res = subprocess.run(cmnd, shell=True, capture_output=True)
                print(res.stdout)
                print(res.stderr)
            if preview or (res.returncode == 0):
                outputs.append(outfile)
                # progress_hook()
            else:
                Logging.log('OptiPass failed:')
                Logging.log(res.stderr)
        self.outputs = outputs

    def collect_results(self, scaled=False):
        '''
        Parse the output files produced by OptiPass (the file names are in
        self.outputs) and collect the results, which are saved in two Pandas
        data frames.
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

        cols = { x: [] for x in ['budget', 'habitat', 'gates']}
        for fn in self.outputs:
            self._parse_op_output(fn, cols)
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
        Return a list of nodes in the path from a barrier to a downstream barrier that
        has no descendants.

        Arguments:
          x: the barrier at the start of the path
          graph:  the digraph with barrier connectivity
        '''
        return [x] + [child for _, child in nx.dfs_edges(graph,x)]

    def _parse_op_output(self, fn, dct):
        '''
        Parse an output file, appending results to the lists.  We need to handle
        two different formats, depending on whether there was one target or more
        than one.

        Arguments:
          fn:  the name of the file to parse
          dct:  a dictionary of column names, results are appended to lists in this dictionary
        '''

        def parse_header_line(line, tag):
            tokens = line.strip().split()
            if not tokens[0].startswith(tag):
                return None
            return tokens[1]

        with open(fn) as f:
            amount = parse_header_line(f.readline(), 'BUDGET')
            dct['budget'].append(float(amount))
            if parse_header_line(f.readline(), 'STATUS') == 'NO_SOLN':
                raise RuntimeError('No solution')
            f.readline()                        # skip OPTGAP
            line = f.readline()
            if line.startswith('PTNL'):
                # dct['weights'].append([1.0])
                hab = parse_header_line(line, 'PTNL_HABITAT')
                dct['habitat'].append(float(hab))
                f.readline()                    # skip NETGAIN
            else:
                lst = []
                while w := parse_header_line(f.readline(), 'TARGET'):
                    lst.append(float(w))
                # dct['weights'].append(lst)
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

        Arguments:
          tlist:  list of target IDs
          scaled:  True if we should create weighted potential habitat values
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
    

    def _ah(self, target, data, scaled):
        """
        Compute the available habitat for a target, in the form of
        a vector of habitat values for each budget level;

        Arguments:
          target:  a Target object (with ID and names of data columns to use)
          data:  the barrier dataframe
          scaled:  if True is the scaled benefit column
        """
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
        return { n: OP.format_budget_amount(n) for n in cols }
    
    dollar_format = {
        'thou':  (1000, 'K'),
        'mil':   (1000000, 'M'),
    }

    @staticmethod
    def format_budget_amount(n):
        divisor, suffix = OP.dollar_format['mil'] if n >= 1000000 else OP.dollar_format['thou']
        s = '${:}'.format(n/divisor)
        if s.endswith('.0'):
            s = s[:-2]
        return s+suffix
    
    def make_roi_curves(self):
        """
        Generate ROI plots based on computed benefits.
        """
        figures = []
        download_figures = []

        climate = None

        subtitle = 'Region: ' if len(self.regions) == 1 else 'Regions: '
        subtitle +=  ', '.join(self.regions)

        for i, t in enumerate(self.targets):
            title = t.long
            if t.infra:
                climate = self.climate
                title += f' ({climate} Climate)'
            if self.weighted:
                title += f' ⨉ {int(self.weights[i])}'
            f = self.bokeh_figure(self.summary.budget, self.summary[t.abbrev], title, subtitle, t.label)
            figures.append((t.short, f))
            f = self.pyplot_figure(self.summary.budget, self.summary[t.abbrev], title, subtitle, t.label)
            download_figures.append((t.short, f))

        if len(self.targets) > 1:
            title = 'Combined Potential Benefit'
            if climate:
                title += f' ({climate} Climate)'
            f = self.bokeh_figure(self.summary.budget, self.summary.netgain, title, subtitle, 'Weighted Net Gain')
            figures.insert(0, ('Net', f))
            f = self.pyplot_figure(self.summary.budget, self.summary[t.abbrev], title, subtitle, 'Weighted Net Gain')
            download_figures.insert(0, ('Net', f))

        self.display_figures = figures
        self.download_figures = download_figures
    
    def bokeh_figure(self, x, y, title, subtitle, axis_label):
        H = 400
        W = 400
        LW = 2
        D = 10
    
        f = figure(
            # title=title, 
            x_axis_label='Budget', 
            y_axis_label=axis_label,
            width=W,
            height=H,
            tools = [HoverTool(mode='vline')],
            tooltips = 'Budget @x{$0.0a}, Benefit @y{0.0}',
        )
        f.line(x, y, line_width=LW)
        f.circle(x, y, fill_color='white', size=D)
        f.add_layout(Title(text=subtitle, text_font_style='italic'), 'above')
        f.add_layout(Title(text=title), 'above')
        f.xaxis.formatter = NumeralTickFormatter(format='$0.0a')
        f.toolbar_location = None
        return f
    
    def pyplot_figure(self, x, y, title, subtitle, axis_label):

        def tick_fmt(n, x):
            return OP.format_budget_amount(n)

        LC = '#3c76af'
        H = 4
        W = 4
        LW = 1.25
        D = 7

        fig, ax = plt.subplots(figsize=(H,W))
        fig.suptitle(title, fontsize=11, fontweight='bold')

        ax.grid(linestyle='--', linewidth=0.5)
        ax.plot(x, y, color=LC, linewidth=LW)
        ax.plot(x, y, 'o', markerfacecolor='white', markeredgecolor=LC, markersize=D, markeredgewidth=0.75)
        ax.xaxis.set_major_formatter(tick_fmt)
        ax.set_title(subtitle, loc='left', fontstyle='oblique', fontsize= 10)
        ax.set_ylabel(axis_label, style='italic', fontsize=10)
        return fig

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
        op = OP(p, ['Coos'], ['CO','CH'], ['1','1'], 'Current')
        assert op.project == p
        assert op.regions == ['Coos']
        assert op.climate == 'Current'
        assert op.weights == [1,1]
        assert len(op.targets) == 2
        t = op.targets[0]
        assert t.abbrev == 'CO'
        assert t.short == 'Coho'
        assert t.long == 'Coho Streams'

    @staticmethod
    def test_generate_frame():
        '''
        Test the structure of a frame that will be printed as a
        'barrier file' for input to OptiPass
        '''

        p = Project('static/workbook.csv', DataSet.TNC_OR)
        op = OP(p, ['Coos'], ['CO','CH'], ['1','1'], 'Current')
        op.generate_input_frame()
        tf = op.input_frame

        assert list(tf.columns) == ['ID','REG', 'FOCUS', 'DSID', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'ACTION', 'COST', 'POST_CO', 'POST_CH']

    # NOTE:  the OPM project does not have habitat in unscaled ("target") units
    # so the calls to collect_results in these tests need to specify scaled = True

    @staticmethod
    def test_example_1():
        '''
        Test the OPResults class by collecting results for Example 1 from the 
        OptiPass User Manual.
        '''
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1'], ['1'], None)
        op.input_frame = pd.read_csv('static/Example_1/Example1.txt', sep='\t')
        op.outputs = sorted(glob('static/Example_1/example_*.txt'))
        op.collect_results(scaled=True)

        assert len(op.targets) == 1
        assert op.targets[0].abbrev == 'T1'
        # assert len(op.weights) == 1 and round(op.weights[0]) == 1

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
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1','T2'], ['3','1'], None)
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
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1'], ['1'], None)
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
        op = OP(Project('static/test_wb.csv', DataSet.OPM), ['OPM'], ['T1','T2'], ['3','1'], None)
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
