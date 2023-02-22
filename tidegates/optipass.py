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

import pandas as pd
import numpy as np
import networkx as nx

from messages import Logging
from barriers import Barriers

class OP:

    def __init__(self, barriers: Barriers, regions: list[str], targets: list[str], climate: str):
        '''
        Instatiate a new OP object.
        * barriers is a Barriers object containing barrier data
        * regions is a list of unique names from the barrier file
        * targets is a list of 2-letter target IDs
        * climate is either 'Current' or 'Future'
        '''
        self.barriers = barriers
        self.regions = regions
        structs = self.barriers.targets[climate]
        self.targets = [structs[t] for t in targets]
        self.climate = climate
        self.input_frame = None
        self.barrier_file = None
        self.outputs = None

    def generate_input_frame(self):
        '''
        Create a data frame that will be written in the format of a "barrier
        file" that will be read by OptiPass.  Save the frame as the
        input_frame attribute of the object.
        '''

        filtered = self.barriers.data[self.barriers.data.REGION.isin(self.regions)]
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

    def run(self, budgets: list[int], preview: bool = False):
        '''
        Generate and execute the shell commands that run OptiPass.
        '''
        df = self.generate_input_frame()
        _, barrier_file = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        df.to_csv(barrier_file, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

        budget_max, budget_delta = budgets
        num_budgets = budget_max // budget_delta
        outputs = []
        root, _ = os.path.splitext(barrier_file)
        for i in range(num_budgets + 1):
            outfile = f'{root}_{i+1}.txt'
            budget = budget_delta * i
            cmnd = f'wine bin/OptiPassMain.exe -f {barrier_file} -o {outfile} -b {budget}'
            if (num_targets := len(self.targets)) > 1:
                cmnd += ' -t {}'.format(num_targets)
                cmnd += ' -w' + ' 1.0' * num_targets
            Logging.log(cmnd)
            if not preview:
                res = subprocess.run(cmnd, shell=True, capture_output=True)
            if preview or (res.returncode == 0):
                outputs.append(outfile)
            else:
                Logging.log('OptiPass failed:')
                Logging.log(res.stderr)
        self.barrier_file = barrier_file
        self.outputs = outputs

    def collect_results(self, base=None):
        '''
        Parse the output files produced by OptiPass, collect results 
        in an OPResults object.
        '''
        pass

class OPResults:
    '''
    Collected results of a series of optimizations at diffent budget levels.
    '''

    def __init__(self, input, outputs):
        '''
        Pass the constructor the name of the input file ("barrier file") passed
        to OptiPass and the list of names of files it generated as outputs.
        '''

        df = pd.read_csv(input, sep='\t')

        G = nx.from_pandas_edgelist(
            df[df.DSID.notnull()], 
            source='ID', 
            target='DSID', 
            create_using=nx.DiGraph
        )

        self.barriers = df.set_index('ID')
        self.paths = { n: self._path_from(n,G) for n in G.nodes }
        self.targets = [col[4:] for col in self.barriers.columns if col.startswith('HAB_')]
        
        cols = { x: [] for x in ['budget', 'weights', 'habitat', 'gates']}
        for fn in outputs:
            self._parse_op_output(fn, cols)
        self.weights = cols['weights'][0]           # should all be the same

        del cols['weights']
        self.summary = pd.DataFrame(cols)
        
        dct = {}
        for i in range(len(self.summary)):
            b = int(self.summary.budget[i])
            dct[b] = [ 1 if g in self.summary.gates[i] else 0 for g in self.barriers.index]
        self.matrix = pd.DataFrame(dct, index=self.barriers.index)

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
                dct['habitat'] = float(hab)
                f.readline()                    # skip WT_NETGAIN
            f.readline()                        # skip blank line
            f.readline()                        # skip header
            lst = []
            while line := f.readline():
                name, action = line.strip().split()
                if action == '1':
                    lst.append(name)
            dct['gates'].append(lst)

    def potential_habitat(self, hf):
        '''
        Compute the potential habitat available after restoration using
        values found by the optimizer.  The argument hf ("habitat frame")
        has one column of habitat values for each restoration target.  The
        method adds columns of computed potential habitats to the summary
        matrix.
        '''
        wph = np.zeros(len(hf))
        for i in range(len(hf.columns)):
            t = self.targets[i]
            cp = self._cp(t, hf.iloc[:,i])
            wph += (self.weights[i] * cp)
            col = pd.DataFrame({t: cp})
            self.summary = pd.concat([self.summary, col], axis = 1)
        self.summary = pd.concat([self.summary, pd.DataFrame({'wph': wph})], axis = 1)
        return self.summary

    def _cp(self, target, habitats):
        res = np.zeros(len(habitats))
        m = self.matrix
        for i in range(len(self.summary.budget)):
            post = self.barriers[m.iloc[:,i]==1][f'POST_{target}']
            pre = self.barriers[m.iloc[:,i]==0][f'PRE_{target}']
            pvec = pd.concat([post, pre])
            res[i] = sum([pvec[self.paths[b]].prod() * habitats[b] for b in self.matrix.index])
        return res

####################
#
# Tests
#

import pytest
import tempfile

class TestOP:

    @staticmethod
    def test_instantiate_object():
        '''
        Test the OP constructor.
        '''
        load_barriers('static/test_barriers.csv')


    @staticmethod
    def test_generate_file():
        '''
        Write a barrier file, test its structure
        '''

        # Create barrier descriptions from the test data
        load_barriers('static/test_barriers.csv')
        bf = generate_input_frame(climate='Current', regions=['Coos'], targets=['CO', 'CH'])

        # Write the frame to a CSV file
        _, path = tempfile.mkstemp(suffix='.txt', dir='./tmp', text=True)
        bf.to_csv(path, index=False, sep='\t', lineterminator=os.linesep, na_rep='NA')

        # Read the file, test its expected structure      
        tf = pd.read_csv(path, sep='\t')

        assert len(tf) == 10
        assert list(tf.columns) == ['ID','REG', 'FOCUS', 'DSID', 'HAB_CO', 'HAB_CH', 'PRE_CO', 'PRE_CH', 'NPROJ', 'ACTION', 'COST', 'POST_CO', 'POST_CH']
        assert tf.COST.sum() == 985000
        assert round(tf.HAB_CO.sum(), 3) ==  0.298

    @staticmethod
    def test_example_1():
        '''
        Test the OPResults class by collecting results for Example 1 from the 
        OptiPass User Manual
        '''
        obj = OPResults('static/Example_1/Example1.txt', sorted(glob('static/Example_1/example_*.txt')))
        assert obj.targets == ['T1']
        assert len(obj.weights) == 1 and round(obj.weights[0]) == 1

        assert type(obj.summary) == pd.DataFrame
        assert len(obj.summary) == 6
        assert round(obj.summary.budget.sum()) == 1500
        assert round(obj.summary.habitat.sum(),2) == 23.30

        assert list(obj.matrix.columns) == list(obj.summary.budget)
        # these comprehensions make lists of budgets where a specified gate was selected
        assert [b for b in obj.matrix.columns if obj.matrix.loc['A',b]] == [400,500]
        assert [b for b in obj.matrix.columns if obj.matrix.loc['D',b]] == [ ]
        assert [b for b in obj.matrix.columns if obj.matrix.loc['E',b]] == [100,300]

        assert obj.paths['E'] == ['E','D','A']
        assert obj.paths['A'] == ['A']

    @staticmethod
    def test_example_4():
        '''
        Same as test_example_1, but using Example 4, which has two restoration targets.
        '''
        obj = OPResults('static/Example_4/Example4.txt', sorted(glob('static/Example_4/example_*.txt')))
        assert obj.targets == ['T1', 'T2']
        assert len(obj.weights) == 2 and round(sum(obj.weights)) == 4

        assert type(obj.summary) == pd.DataFrame
        assert len(obj.summary) == 6
        assert round(obj.summary.budget.sum()) == 1500
        assert round(obj.summary.habitat.sum(),2) == 197.62

        # using two targets does not change the gate selections
        assert [b for b in obj.matrix.columns if obj.matrix.loc['A',b]] == [400,500]
        assert [b for b in obj.matrix.columns if obj.matrix.loc['D',b]] == [ ]
        assert [b for b in obj.matrix.columns if obj.matrix.loc['E',b]] == [100,300]

    @staticmethod
    def test_collect_results():
        '''
        Test the function that collects results from individual runs into a single
        data frame.  Expects to find 6 files in ./static/Example1 (named for the 
        example data in the OptiPass User Manual)
        '''
        files = glob('static/Example_1/example_*.txt')
        assert len(files) == 6
    
    @staticmethod
    def test_potential_habitat_1():
        '''
        Test the method that computes potential habitat, using the results 
        genearated for Example 1 in the OptiPass manual.
        '''
        obj = OPResults('static/Example_1/Example1.txt', sorted(glob('static/Example_1/example_*.txt')))
        m = obj.potential_habitat(obj.barriers[['HAB_T1']])
        assert len(m) == 6
        assert 'T1' in m.columns and 'wph' in m.columns
        assert round(m.wph[0],3) == 1.238
        assert round(m.wph[5],3) == 8.520

    @staticmethod
    def test_potential_habitat_4():
        '''
        Same as test_potential_habitat_1, but using Example 4, with two restoration targets
        '''
        obj = OPResults('static/Example_4/Example4.txt', sorted(glob('static/Example_4/example_*.txt')))
        m = obj.potential_habitat(obj.barriers[['HAB_T1','HAB_T2']])
        assert len(m) == 6
        assert 'T1' in m.columns and 'T2' in m.columns and 'wph' in m.columns
        assert round(m.wph[0],3) == 5.491
        assert round(m.wph[4],3) == 21.084    # the value shown in the OP manual
