import param

import panel as pn
from panel.layout.gridstack import GridStack

# import folium as fm
import numpy as np
import pandas as pd

import bokeh.plotting as bk
import bokeh.layouts as layouts
from bokeh.models import NumeralTickFormatter, Circle
from bokeh.models.widgets.tables import BooleanFormatter
from bokeh.tile_providers import get_provider
import xyzservices.providers as xyz

import os
import re
import subprocess
import sys
import time

from barriers import load_barriers, BF

pn.extension('gridstack', 'tabulator')

class TGMap():
    def __init__(self):
        load_barriers('static/source_data.csv')
        self.map, self.dots = self._create_map()

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

results_empty_text = '''
<h2>Optimizer Output</h2>

<p>The output from OptiPass will be displayed here.</p>

<p>To run OptiPass enter optimization parameters in the Start panel, then click the <b>Optimize</b> button.
'''

results_pending_text = '''
<h2>⏳ Optimizer Output</h2>

<p>Waiting for OptiPass to finish...</p>
'''

results_failed_text = '''
<h2>💣 Optimizer Failed</h2>

<p>Something went wrong when running OptiPass or parsing its outputs.</p>
'''


class TideGates(param.Parameterized):
    map = TGMap()
    map_pane = pn.Pane(map.graphic())

    optimize_button = pn.widgets.Button(name='Optimize', height=40, width=60, background='#b2d2dd')
    load_button = pn.widgets.Button(name='Load',height=40,width=60)
    save_button = pn.widgets.Button(name='Save',height=40,width=60)
    reset_button = pn.widgets.Button(name='Reset',height=40,width=60)

    climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=BF.climates, inline=False)
    region_group = pn.widgets.CheckBoxGroup(name='Regions', options=BF.regions, inline=False)

    target_boxes = pn.widgets.CheckBoxGroup(name='Targets', options=list(BF.target_map.keys()), inline=False)

    region_alert = pn.pane.Alert('**No geographic regions selected**', alert_type='danger')
    target_alert = pn.pane.Alert('**No optimizer targets selected**', alert_type='danger')
    success_alert = pn.pane.Alert('**Optimization complete.**  <br/>Click on "Plots" or "Table" at the top of this window to view the results.', alert_type='success')

    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        start_tab = pn.Column(
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
            pn.WidgetBox(
                BudgetBox()
            ),

            pn.Row(self.success_alert),
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
        self.region_alert.visible = False
        self.target_alert.visible = False
        self.region_group.param.watch(self.region_cb, ['value'])
        self.optimize_button.on_click(self.run_optimizer)

    def region_cb(self, *events):
        self.map.display_regions(events[0].new)

    def run_optimizer(self, _):
        if not self.check_selections():
            return
        self.success_alert.visible = False
        self.main[1].loading = True
        time.sleep(1)
        cmnd = f'python3 bin/parse_optipass_results.py static/CoquilleInundCoho_run_results.txt'
        result = subprocess.run(cmnd, shell=True, capture_output=True)
        p = OptiPassOutput()
        if result.returncode == 0:
            p.parse_output(result.stdout.decode())
            col = pn.Column(
                pn.Pane(p.roi_curves(), width=500, height=800),
                # pn.widgets.IntSlider(name='', start=0, end=len(p.x), step=1, value=0, tooltips=False)
            )
            self.main.append(('Plots',col))
            self.main.append(('Table', self.make_table_tab(p.as_df(), p.targets)))
        else:
            self.main.append(('Output',pn.Pane(results_failed_text, width=500)))
        self.main[1].loading = False
        self.success_alert.visible = True
        self.map.set_selection(['039Ats1'])

    def table_click_cb(self, *events):
        print('table cb', len(events), events[0])

    def make_table_tab(self, df, targets):
        formatters = { }
        alignment = {}
        print(df.columns)
        for col in df.columns:
            if re.match(r'[\d\.]+', col):
                formatters[col] = {'type': 'tickCross', 'crossElement': ''}
                alignment[col] = 'center'
            elif col in targets:
                # print('target', col, 'max', df[col].max())
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

class BudgetBox(pn.Row):
    def __init__(self):
        super(BudgetBox, self).__init__()
        self.budget = pn.widgets.IntSlider(name='Maximum', start=0, end=5000000, step=100000, value=0, tooltips=False, format='$0,000', width=400)
        self.increment = pn.widgets.RadioBoxGroup(options=['$50,000', '$100,000', '$250,000', '$500,000'], width=100)
        self.increment.param.watch(self.increment_cb, ['value'])
        self.append(self.budget)
        self.append(pn.Spacer(width=50))
        self.append(self.increment)

    def increment_cb(self, *events):
        amt = events[0].new.replace(',', '')
        self.budget.step = int(amt[1:])

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
