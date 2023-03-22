import param

import panel as pn
from panel.layout.gridstack import GridStack

# import folium as fm
import numpy as np
import pandas as pd

import bokeh.plotting as bk
import bokeh.layouts as layouts
from bokeh.models import Circle
from bokeh.models.formatters import NumeralTickFormatter
from bokeh.models.widgets.tables import NumberFormatter
from bokeh.tile_providers import get_provider
import xyzservices.providers as xyz

from glob import glob
from math import ceil
import os
import re

from targets import DataSet
from project import Project
from optipass import OP
from messages import Logging

pn.extension('gridstack', 'tabulator')

class TGMap():
    def __init__(self, bf):
        Logging.log('initializing...')
        Logging.log('...project')
        self.map, self.dots = self._create_map(bf)
        Logging.log('...map')

    def graphic(self):
        return self.map

    def _create_map(self, bf):
        tile_provider = get_provider(xyz.OpenStreetMap.Mapnik)
        p = bk.figure(
            title='Oregon Coast', 
            height=800,
            width=400,
            x_range=(bf.map_info.x.min(),bf.map_info.x.max()), 
            y_range=(bf.map_info.y.min()*0.997,bf.map_info.y.max()*1.003),
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
        for r in bf.regions:
            df = bf.map_info[bf.map_info.region == r]
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


class BudgetBox(pn.Column):
    def __init__(self):
        super(BudgetBox, self).__init__()
        # self.budget = pn.widgets.FloatSlider(
        #     start=0, 
        #     end=0.1, 
        #     step=0.1, 
        #     value=0, 
        #     tooltips=False, 
        #     format=NumeralTickFormatter(format='$0,0'), 
        #     width=400
        # )
        self.max = pn.widgets.StaticText(value='<b>Upper Limit:</b>  $0')
        self.budget = pn.widgets.FloatInput(
            name='Budget',
            value=0,
            end=0,
            width=175,
            format='$0,0',
        )
        self.steps = pn.widgets.IntInput(
            name='Steps',
            value=10,
            width=75,
            step=1,
        )
        # self.step_size = pn.widgets.FloatInput(
        #     name='Step Size',
        #     width=125,
        #     format='$0,0'
        # )
        self.budget.param.watch(self.cb, ['value'])
        self.steps.param.watch(self.cb, ['value'])
        # self.step_size_entry.param.watch(self.cb, ['value'])
        self.step_size = 0
        self.step_size_text = pn.widgets.StaticText(value=f'Step Size:  $0')

        # Version 1:  Slider with limit display
        # self.append(pn.Row(
        #     self.budget,
        #     self.max,
        # ))

        # Version 2:  FloatEntry boxes
        self.append(self.max)
        self.append(pn.Row(
            self.budget, 
            pn.layout.Spacer(width=30), 
            self.steps, 
            self.step_size_text,
        ))
        self.append(pn.layout.VSpacer(height=10))

    def set_step_size_text(self, n):
        print('setting step size text', n)
        self.step_size_text.value = f'Step Size:  ${n:,}'

    def set_limit(self, n):
        self.max.value = f'<b>Upper Limit:</b>  ${n:,}'

        # Version 1:  set slider params
        # n = round(n/1000000,1)
        # self.budget.end = n
        # if n >= 20:
        #     self.budget.step = 1.0
        # elif n >= 10:
        #     self.budget.step = 0.5
        # elif n >= 5:
        #     self.budget.step = 0.25
        # else:
        #     self.budget.step = 0.1

        # Version 2: Update entry boxes
        blk =  1000000 if n < 20000000 else 10000000
        amt = (ceil(n / (2*blk)))*blk
        self.budget.end = n
        self.budget.value = amt          # triggers callback to set step size
        self.budget.step = self.step_size

    def cb(self, *events):
        print(events)
        print('current', self.budget.value, self.steps.value, self.step_size)
        self.step_size = int(self.budget.value / self.steps.value)
        self.set_step_size_text(self.step_size)

    def values(self):
        return self.budget.value, int(self.increment.value.replace('$','').replace(',',''))
 
class RegionBox(pn.Column):
    
    def __init__(self, project, map, budget):
        super(RegionBox, self).__init__()
        self.totals = project.totals
        self.map = map
        self.budget_box = budget
        self.grid = pn.GridBox(ncols=3)
        for name in project.regions:
            cost = round(project.totals[name]/1000000,1)
            box = pn.widgets.Checkbox(name=name)
            amt = pn.widgets.StaticText(value=f'${cost}M', align='end')
            self.grid.objects.extend([box, pn.Spacer(width=50), amt])
            box.param.watch(self.cb, ['value'])
        self.selected = set()
        self.sum = pn.widgets.StaticText(value='Total:  $0M')
        self.append(self.grid)
        # self.append(self.sum)
        # self.append(self.budget)

    def cb(self, *events):
        for e in events:
            if e.type == 'changed':
                r = e.obj.name
                if e.new:
                    self.selected.add(r)
                else:
                    self.selected.remove(r)
                amount = sum(self.totals[x] for x in self.selected)
                self.budget_box.set_limit(amount)
        self.map.display_regions(self.selected)

welcome_text = '''
<h2>Welcome</h2>

<p>Click on the Start tab above to enter optimization parameters and run the optimizer.</p>
'''

button_text = '''
<p style="margin-top: 0">
   Select one or more regions (at least one is required).  The dollar amount
   next to a region name is the total cost for every barrier in that region.
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

class TideGates(param.Parameterized):


    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.bf = Project('static/workbook.csv', DataSet.TNC_OR)

        self.map = TGMap(self.bf)
        self.map_pane = pn.Pane(self.map.graphic())

        self.optimize_button = pn.widgets.Button(name='Optimize', height=40, width=60, background='#b2d2dd')
        self.load_button = pn.widgets.Button(name='Load',height=40,width=60)
        self.save_button = pn.widgets.Button(name='Save',height=40,width=60)
        self.reset_button = pn.widgets.Button(name='Reset',height=40,width=60)

        self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=self.bf.climates, inline=False)
        self.budget_box = BudgetBox()
        self.regions = RegionBox(self.bf, self.map, self.budget_box)

        self.target_boxes = pn.widgets.CheckBoxGroup(name='Targets', options=list(self.bf.target_map.keys()), inline=False)

        self.region_alert = pn.pane.Alert('**No geographic regions selected**', alert_type='danger')
        self.target_alert = pn.pane.Alert('**No optimizer targets selected**', alert_type='danger')
        self.success_alert = pn.pane.Alert('**Optimization complete.**  <br/>Click the "Output" tab at the top of this window to view the results.', alert_type='success')
        self.fail_alert = pn.pane.Alert('**Optimization failed.**  <br/>One or more calls to OptiPass did not succeed (see log for explanation).', alert_type='danger')
        
        self.info = pn.widgets.StaticText(value='')

        start_tab = pn.Column(
            # pn.Row(self.info),
            pn.Row('<h3>Geographic regions</h3>'),
            pn.Pane(button_text,width=500),
            pn.WidgetBox(self.regions),

            # pn.layout.VSpacer(height=5),
            pn.Row('<h3>Budget</h3>'),
            # pn.Pane(budget_text, width=500),
            pn.WidgetBox(self.budget_box, width=500),

            # pn.layout.VSpacer(height=5),
            pn.Row('<h3>Restoration targets</h3>'),
            pn.Pane(target_text, width=500),
            pn.WidgetBox(self.target_boxes, width=500),

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
            sizing_mode = 'fixed',
        )

        self.success_alert.visible = False
        self.fail_alert.visible = False
        self.region_alert.visible = False
        self.target_alert.visible = False
        # self.region_group.param.watch(self.region_cb, ['value'])
        self.optimize_button.on_click(self.run_optimizer)
        self.optimizer_clicks = set()

    # def region_cb(self, *events):
    #     self.map.display_regions(events[0].new)

    def run_optimizer(self, _):
        Logging.log('running optimizer')

        if not self.check_selections():
            return

        self.success_alert.visible = False
        self.main[1].loading = True

        budget_max, budget_delta = self.budget_box.values()
        num_budgets = budget_max // budget_delta

        self.op = OP(
            self.bf, 
            # self.region_group.value,
            list(self.regions.selected),
            [self.bf.target_map[t] for t in self.target_boxes.value],
            self.climate_group.value,
        )
        self.op.generate_input_frame()
        if base := os.environ.get('OP_OUTPUT'):
            self._find_output_files(base)
            self.op.budget_delta = budget_delta
            self.op.budget_max = budget_max
        else:
            self.op.run(self.budget_box.values())
        self.op.collect_results()

        self.main[1].loading = False

        # Expect to find one file for each budget level plus one more
        # for the $0 budget

        if len(self.op.outputs) == num_budgets+1:
            Logging.log('Output files:' + ','.join(self.op.outputs))
            self.add_output_pane()
            self.success_alert.visible = True
        else:
            self.fail_alert.visible = True


    # When debugging outside of a container define an environment variable
    # named OP_OUTPUT, setting it to the base name of a set of existing output 
    # files.  This helper function collects the file names so they can be
    # used in the display

    def _find_output_files(self, pattern):
        def number_part(fn):
            return int(re.search(r'_(\d+)\.txt$', fn).group(1))

        outputs = glob(f'tmp/{pattern}_*.txt')
        self.op.outputs = sorted(outputs, key=number_part)

    def table_click_cb(self, *events):
        Logging.log('table cb', len(events), events[0])

    # After running OptiPass call these two methods to add tabs to the main
    # panel to show the results.

    def add_output_pane(self):
        formatters = { }
        alignment = { }
        df = self.op.table_view()
        for col in df.columns:
            if col.startswith('$') or col in ['Primary','Dominant']:
                formatters[col] = {'type': 'tickCross', 'crossElement': ''}
                alignment[col] = 'center'
            # elif col in targets:
            #     # Logging.log('target', col, 'max', df[col].max())
            #     formatters[col] = {'type': 'progress', 'max': df[col].max(), 'color': '#3c76af'}
            elif col.endswith(('hab','gain','tude')):
                formatters[col] = NumberFormatter(format='0.00')
                alignment[col] = 'right'
            elif col == 'Cost':
                formatters[col] = {'type': 'money', 'symbol': '$', 'precision': 0}
        table = pn.widgets.Tabulator(
            df, 
            show_index=False, 
            frozen_columns=['ID'],
            formatters=formatters,
            text_align=alignment,
            configuration={'columnDefaults': {'headerSort': False}},
            sorters = [ ],
        )
        table.on_click(self.table_click_cb)
        table.disabled = True

        output = pn.Column(
            pn.layout.VSpacer(height=20),
            self.op.roi_curves(), 
            pn.layout.VSpacer(height=30),
           table
        )

        self.main.append(('Output', pn.Pane(output, min_width=500, height=800)))

    def check_selections(self):
        self.region_alert.visible = False
        self.target_alert.visible = False
        # if self.region_group.value == []:
        if len(self.regions.selected) == 0:
            self.region_alert.visible = True
        if len(self.target_boxes.value) == 0:
            self.target_alert.visible = True
        return not (self.region_alert.visible or self.target_alert.visible)
