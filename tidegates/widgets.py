import param

import panel as pn
from panel.layout.gridstack import GridStack

# import folium as fm
import numpy as np
import pandas as pd
import tempfile

import bokeh.plotting as bk
import bokeh.layouts as layouts
from bokeh.models import NumeralTickFormatter, Circle
from bokeh.models.widgets.tables import BooleanFormatter
from bokeh.tile_providers import get_provider
import xyzservices.providers as xyz

import os
import re

from barriers import load_barriers, BF
from optipass import generate_barrier_frame, run_OP, parse_results
from messages import Logging

pn.extension('gridstack', 'tabulator')

class TGMap():
    def __init__(self):
        Logging.log('initializing...')
        load_barriers('static/workbook.csv')
        Logging.log('...barriers')
        self.map, self.dots = self._create_map()
        Logging.log('...map')

    def graphic(self):
        return self.map

    def _create_map(self):
        tile_provider = get_provider(xyz.OpenStreetMap.Mapnik)
        p = bk.figure(
            title='Oregon Coast', 
            height=800,
            width=400,
            x_range=(BF.map_info.x.min(),BF.map_info.x.max()), 
            y_range=(BF.map_info.y.min()*0.997,BF.map_info.y.max()*1.003),
            x_axis_type='mercator',
            y_axis_type='mercator',
            toolbar_location='below',
            tools=['pan','wheel_zoom','hover','reset'],
            tooltips = [
                ("ID", "@id"),
                ("Region", "@region"),
                ("Type", "@type"),
            ]
        )
        p.add_tile(tile_provider)
        p.toolbar.autohide = True
        dots = { }
        for r in BF.regions:
            df = BF.map_info[BF.map_info.region == r]
            c = p.circle('x', 'y', size=5, color='darkslategray', source=df, tags=list(df.id))
            c.nonselection_glyph = Circle(size=5, fill_color='darkslategray')
            c.selection_glyph = Circle(size=8, fill_color='blue')
            dots[r] = c
            c.visible = False
        return p, dots

    def display_regions(self, lst):
        for r, dots in self.dots.items():
            dots.visible = r in lst

    def set_selection(self, lst):
        self.map.select({'tag': lst[0]})


class BudgetBox(pn.Row):
    def __init__(self):
        super(BudgetBox, self).__init__()
        self.budget = pn.widgets.IntSlider(name='Maximum', start=50000, end=5000000, step=100000, value=50000, tooltips=False, format='$0,000', width=400)
        self.increment = pn.widgets.RadioBoxGroup(options=['$50,000', '$100,000', '$250,000', '$500,000'], width=100)
        self.increment.param.watch(self.increment_cb, ['value'])
        self.append(self.budget)
        self.append(pn.Spacer(width=50))
        self.append(self.increment)

    def increment_cb(self, *events):
        amt = events[0].new.replace(',', '')
        self.budget.step = int(amt[1:])
        self.budget.start = self.budget.step
        self.budget.value = self.budget.step

    def values(self):
        return self.budget.value, int(self.increment.value.replace('$','').replace(',',''))


welcome_text = '''
<h2>Welcome</h2>

<p>Click on the Start tab above to enter optimization parameters and run the optimizer.</p>
'''

button_text = '''
<p style="margin-top: 0">
   Select one or more estuary names (at least one is required) and an optional climate scenario.
</p>
'''

target_text = '''
<p>
   Select one or more restoration targets.
</p>
'''

budget_text = '''
<p>
   Select the maximum project budget and the budget increments.
</p>
'''

# results_empty_text = '''
# <h2>Optimizer Output</h2>

# <p>The output from OptiPass will be displayed here.</p>

# <p>To run OptiPass enter optimization parameters in the Start panel, then click the <b>Optimize</b> button.
# '''

# results_pending_text = '''
# <h2>⏳ Optimizer Output</h2>

# <p>Waiting for OptiPass to finish...</p>
# '''

# results_failed_text = '''
# <h2>💣 Optimizer Failed</h2>

# <p>Something went wrong when running OptiPass or parsing its outputs.</p>
# '''


class TideGates(param.Parameterized):


    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.map = TGMap()
        self.map_pane = pn.Pane(self.map.graphic())

        self.optimize_button = pn.widgets.Button(name='Optimize', height=40, width=60, background='#b2d2dd')
        self.load_button = pn.widgets.Button(name='Load',height=40,width=60)
        self.save_button = pn.widgets.Button(name='Save',height=40,width=60)
        self.reset_button = pn.widgets.Button(name='Reset',height=40,width=60)

        self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=BF.climates, inline=False)
        self.region_group = pn.widgets.CheckBoxGroup(name='Regions', options=BF.regions, inline=False)

        self.target_boxes = pn.widgets.CheckBoxGroup(name='Targets', options=list(BF.target_map.keys()), inline=False)
        self.budget_box = BudgetBox()

        self.region_alert = pn.pane.Alert('**No geographic regions selected**', alert_type='danger')
        self.target_alert = pn.pane.Alert('**No optimizer targets selected**', alert_type='danger')
        self.success_alert = pn.pane.Alert('**Optimization complete.**  <br/>Click on "Plots" or "Table" at the top of this window to view the results.', alert_type='success')
        self.fail_alert = pn.pane.Alert('**Optimization failed.**  <br/>One or more calls to OptiPass did not succeed (see log for explanation).', alert_type='danger')
        
        self.info = pn.widgets.StaticText(value='')

        start_tab = pn.Column(
            pn.Row(self.info),
            pn.layout.VSpacer(),
            pn.Row('<h3>Geographic region and climate scenario</h3>'),
            pn.Row(
                pn.Pane(button_text,width=200),
                pn.WidgetBox(self.region_group, width=150),
                pn.WidgetBox(self.climate_group, width=100),
            ),

            pn.layout.VSpacer(),
            pn.Row('<h3>Restoration targets</h3>'),
            pn.Pane(target_text, width=500),
            pn.WidgetBox(self.target_boxes, width=500),

            pn.layout.VSpacer(),
            pn.Row('<h3>Budget</h3>'),
            pn.Pane(budget_text, width=500),
            pn.WidgetBox(self.budget_box),

            pn.Row(self.success_alert),
            pn.Row(self.fail_alert),
            pn.Row(self.region_alert),
            pn.Row(self.target_alert),
            pn.Row(pn.layout.Spacer(width=200), self.optimize_button, width=500),
        )

        self.main = pn.Tabs(
            ('Home', pn.Pane(welcome_text)),
            ('Start', start_tab),
            min_width=800,
            sizing_mode = 'stretch_both',
        )

        self.success_alert.visible = False
        self.fail_alert.visible = False
        self.region_alert.visible = False
        self.target_alert.visible = False
        self.region_group.param.watch(self.region_cb, ['value'])
        self.optimize_button.on_click(self.run_optimizer)
        self.optimizer_clicks = set()

    def region_cb(self, *events):
        self.map.display_regions(events[0].new)

    def run_optimizer(self, _):
        Logging.log('running optimizer')

        if not self.check_selections():
            return

        self.success_alert.visible = False
        self.main[1].loading = True

        tlist = [BF.target_map[t] for t in self.target_boxes.value]

        res = run_OP(
            regions=self.region_group.value,
            targets=tlist,
            climate=self.climate_group.value,
            budgets=self.budget_box.values()
        )

        self.main[1].loading = False

        if len(res) == len(tlist):
            self.success_alert.visible = True
        else:
            self.fail_alert.visible = True

        Logging.log('done')

    def table_click_cb(self, *events):
        Logging.log('table cb', len(events), events[0])

    def make_table_tab(self, df, targets):
        formatters = { }
        alignment = {}
        Logging.log(df.columns)
        for col in df.columns:
            if re.match(r'[\d\.]+', col):
                formatters[col] = {'type': 'tickCross', 'crossElement': ''}
                alignment[col] = 'center'
            elif col in targets:
                # Logging.log('target', col, 'max', df[col].max())
                formatters[col] = {'type': 'progress', 'max': df[col].max(), 'color': '#3c76af'}
            elif col == 'Cost':
                formatters[col] = {'type': 'money', 'symbol': '$', 'precision': 0}
        table = pn.widgets.Tabulator(
            df, 
            show_index=False, 
            formatters=formatters,
            text_align=alignment,
            # configuration={'columnDefaults': {'headerSort': False}},
            frozen_columns=['BARID'],
            # sorters = [ {'field': col, 'dir': 'asc'} for col in targets ],
        )
        table.on_click(self.table_click_cb)
        table.disabled = True
        return pn.Pane(table, min_width=500, height=800)

    def check_selections(self):
        self.region_alert.visible = False
        self.target_alert.visible = False
        if self.region_group.value == []:
            self.region_alert.visible = True
        if len(self.target_boxes.value) == 0:
            self.target_alert.visible = True
        return not (self.region_alert.visible or self.target_alert.visible)

class OptiPassOutput:
    def __init__(self):
        self.x = [ ]
        self.y = { }
        self.header = [ ]
        self.table = { }
        self.targets = [ ]
        
    def parse_output(self, s):
        
        def infer_type(s):
            if len(s) == 0:
                return 0
            if re.fullmatch(r'\d+',s):
                return int(s)
            if re.fullmatch(r'[+-]?\d+\.\d+',s):
                return float(s)
            return s
 
        for line in s.split('\n'):
            tokens = line.split(',')
            match tokens[0]:
                case 'x':
                    self.x = [float(x) for x in tokens[1:]]
                case 'y':
                    self.targets.append(tokens[1])
                    self.y[tokens[1]] = [float(x) for x in tokens[2:]]
                case 'h':
                    self.header = tokens[1:]
                    self.table = { s: [] for s in self.header }
                case 't':
                    for i in range(0, len(tokens)-1):
                        col = self.header[i]
                        self.table[col].append(infer_type(tokens[i+1]))
                    
    def as_df(self):
        df = pd.DataFrame(self.table)
        in_solution = df[df.InSoln > 0]
        cols = [
            'BARID',
            # '0.0',
            '1.0',
            '2.0',
            '3.0',
            '4.0',
            '5.0',
            '6.0',
            '7.0',
            '8.0',
            '9.0',
            '10.0',
            'InSoln',
            'Name',
            'Cost',
            'Region',
            'BarrierType',
            'Coho_salmon',          # <=== TODO: get these column names from selected targets
            'InundHab_Current',     # <===
            # 'POINT_X', 
            # 'POINT_Y',
        ]
        # table = pn.widgets.Tabulator(in_solution.loc[:,cols], show_index=False)
        # table.disabled = True
        # return table
        return in_solution.loc[:,cols]

    def roi_curves(self):
        n = len(self.y)
        figs = [layouts.Spacer(height=20)]
        for i, k in enumerate(self.y):
            f = bk.figure(width=600,height=300,title=k)
            # f.line(self.x, self.y[k], line_width=2)
            # f.square(self.x, self.y[k], size=5, fill_color='black')
            f.vbar(x=self.x, top=self.y[k], width=0.6)
            f.xaxis.axis_label = 'budget (millions)'
            f.xaxis.formatter = NumeralTickFormatter(format="$0")
            f.yaxis.axis_label = 'potential benefit (target units)'
            f.tools = []
            figs.append(f)
            figs.append(layouts.Spacer(height=20))
        return layouts.column(*figs)

