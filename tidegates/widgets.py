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

from targets import DataSet, make_layout
from budgets import BasicBudgetBox, AdvancedBudgetBox, FixedBudgetBox
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
            height=900,
            width=425,
            x_range=(bf.map_info.x.min()*0.997,bf.map_info.x.max()*1.003), 
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
        super(BudgetBox, self).__init__(margin=(15,0,15,5))
        self.tabs = pn.Tabs(
            ('Basic', BasicBudgetBox()),
            ('Advanced', AdvancedBudgetBox()),
            ('Fixed', FixedBudgetBox()),
        )
        self.append(self.tabs)

    def set_budget_max(self, n):
        for t in self.tabs:
            t.set_budget_max(n)

    def values(self):
        return self.tabs[self.tabs.active].values()

 
class RegionBox(pn.Column):
    
    def __init__(self, project, map, budget):
        super(RegionBox, self).__init__(margin=(10,0,10,5))
        self.totals = project.totals
        self.map = map
        self.budget_box = budget
        # self.grid = pn.GridBox(ncols=3)
        # for name in project.regions:
        #     cost = round(project.totals[name]/1000000,1)
        #     box = pn.widgets.Checkbox(name=name)
        #     amt = pn.widgets.StaticText(value=f'${cost}M', align='end')
        #     self.grid.objects.extend([box, pn.Spacer(width=50), amt])
        #     box.param.watch(self.cb, ['value'])
        boxes = []
        for name in project.regions:
            box = pn.widgets.Checkbox(name=name)
            box.param.watch(self.cb, ['value'])
            boxes.append(box)
        self.grid = pn.GridBox(*boxes, ncols=2)
        self.selected = set()
        # self.sum = pn.widgets.StaticText(value='Total:  $0M')
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
                self.budget_box.set_budget_max(amount)
        self.map.display_regions(self.selected)

    def selection(self):
        return self.selected

class TargetBox(pn.Column):

    def __init__(self, targets):
        super(TargetBox, self).__init__(margin=(10,0,10,5))
        self.grid = pn.GridBox(ncols=2)
        self.boxes = { }
        for row in make_layout():
            lst = [ ]
            for t in row:
                b = pn.widgets.Checkbox(name=t, width=200)
                lst.append(b)
                self.boxes[t] = b
            self.grid.objects.extend(lst)
        self.append(self.grid)

    def selection(self):
        return [t for t in self.boxes if self.boxes[t].value ]


class InfoBox(pn.Row):

    missing_params_text = '''
    <b>Missing Information</b>

    <p>Please select one or more geographic regions and one or more restoration targets.</p>
    '''

    success_message_text = '''
    <b>Optimization Complete</b>

    <p>Click the "Output" tab at the top of this window to view the results.</p>
    '''

    fail_message_text = '''
    <b>Optimization Failed</b>

    <p>One or more calls to OptiPass did not succeed (see log for explanation).</p>
    '''

    def __init__(self):
        super(InfoBox, self).__init__()
        self.blank = pn.pane.HTML(background='#FFFFFF', width=50, height=50)
        self.missing_params_message = pn.pane.Alert(InfoBox.missing_params_text, alert_type='danger')
        self.success_message = pn.pane.Alert(InfoBox.success_message_text, alert_type='success')
        self.fail_message = pn.pane.Alert(InfoBox.fail_message_text, alert_type='danger')
        self.op_progress_bar = pn.indicators.Progress(name='OP Progress', value=0, max=100, width=300)
        self.erase()

    def erase(self):
        self.clear()
        self.append(self.blank)

    def show_missing(self):
        self.clear()
        self.append(self.missing_params_message)
    
    def show_success(self):
        self.clear()
        self.append(self.success_message)
    
    def show_fail(self):
        self.clear()
        self.append(self.fail_message)

    def show_progress(self, count):
        self.clear()
        self.append(pn.Row(pn.widgets.StaticText(value='<b>Optimizing</b>  '), self.op_progress_bar))
        self.delta = 100 // count

    def update_progress(self):
        self.op_progress_bar.value = min(100, self.op_progress_bar.value + self.delta)


welcome_text = '''
<h2>Welcome</h2>

<p>Click on the Start tab above to enter optimization parameters and run the optimizer.</p>
'''

class TideGates(param.Parameterized):

    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.bf = Project('static/workbook.csv', DataSet.TNC_OR)

        self.map = TGMap(self.bf)
        self.map_pane = pn.panel(self.map.graphic())

        self.optimize_button = pn.widgets.Button(name='Run Optimizer', height=40, width=60, background='#b2d2dd')
        self.load_button = pn.widgets.Button(name='Load',height=40,width=60)
        self.save_button = pn.widgets.Button(name='Save',height=40,width=60)
        self.reset_button = pn.widgets.Button(name='Reset',height=40,width=60)

        self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=self.bf.climates, inline=False)
        self.budget_box = BudgetBox()
        self.region_boxes = RegionBox(self.bf, self.map, self.budget_box)

        # self.target_boxes = pn.widgets.CheckBoxGroup(name='Targets', options=list(self.bf.target_map.keys()), inline=False)
        self.target_boxes = TargetBox(list(self.bf.target_map.keys()))
 
        self.info = InfoBox()

        start_tab = pn.Column(
            # pn.Row(self.info),
            pn.Row('<h3>Geographic Regions</h3>'),
            # pn.panel(region_text,width=500),
            pn.WidgetBox(self.region_boxes, width=600),

            # pn.layout.VSpacer(height=5),
            pn.Row('<h3>Budget</h3>'),
            # pn.panel(budget_text, width=500),
            self.budget_box,

            # pn.layout.VSpacer(height=5),
            pn.Row('<h3>Targets</h3>'),
            # pn.panel(target_text, width=500),
            pn.WidgetBox(
                pn.Row(
                    self.target_boxes,
                    pn.Column(
                        pn.widgets.StaticText(value='<b>Climate Scenario</b>'),
                        self.climate_group, margin=(10,0,20,0)
                    ),
                ),
                width=600,
            ),

            pn.layout.VSpacer(height=20),
            pn.Row(pn.layout.Spacer(width=200), self.optimize_button, width=600),
            pn.layout.VSpacer(height=10),
            self.info,
        )

        self.main = pn.Tabs(
            ('Home', pn.panel(welcome_text)),
            ('Start', start_tab),
            sizing_mode = 'fixed',
            width=800,
            height=800,
        )

        self.optimize_button.on_click(self.run_optimizer)


    def run_optimizer(self, _):
        Logging.log('running optimizer')

        self.info.erase()

        if len(self.region_boxes.selection()) == 0 or len(self.target_boxes.selection()) == 0:
            self.info.show_missing()
            return

        self.main[1].loading = True

        budget_max, budget_delta = self.budget_box.values()
        num_budgets = budget_max // budget_delta

        # Uncomment this line to show a progress bar below the Optimize button (and uncomment
        # the line below that updates the bar after each optimizer run)
        # self.info.show_progress(num_budgets)

        self.op = OP(
            self.bf, 
            list(self.region_boxes.selection()),
            [self.bf.target_map[t] for t in self.target_boxes.selection()],
            self.climate_group.value,
        )
        self.op.generate_input_frame()
        if base := os.environ.get('OP_OUTPUT'):
            self._find_output_files(base)
            self.op.budget_delta = budget_delta
            self.op.budget_max = budget_max
        else:
            # Uncomment one of the following lines, depending on whether the progress
            # bar is displayed
            # self.op.run(self.budget_box.values(), False, self.info.update_progress)
            self.op.run(self.budget_box.values(), False)

        self.main[1].loading = False

        # If OP ran successfully we expect to find one file for each budget level 
        # plus one more for the $0 budget

        if self.op.outputs is not None and len(self.op.outputs) == num_budgets+1:
            Logging.log('runs complete')
            self.op.collect_results(False)
            Logging.log('Output files:' + ','.join(self.op.outputs))
            self.add_output_pane()
            self.info.show_success()
        else:
            self.info.show_fail()

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

        self.main.append(('Output', pn.panel(output, min_width=500, height=800)))
