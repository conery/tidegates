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
        super(BudgetBox, self).__init__()
        self.tabs = pn.Tabs(
            ('Basic', BasicBudgetBox()),
            ('Advanced', AdvancedBudgetBox()),
            ('Fixed', FixedBudgetBox()),
        )
        self.append(self.tabs)

    @staticmethod
    def format_budget_amount(n):
        n = int(n)
        if n >= 1000000:
            x = n / 1000000
            s = f'${x:.1f}M' if (n % 1000000) else f'${x:.0f}M'
        elif n >= 1000:
            x = n / 1000
            s = f'${x:.1f}K' if (n % 1000) else f'${x:.0f}K'
        else:
            s = f'${n}'
        return s

    def set_budget_max(self, n):
        for t in self.tabs:
            t.set_budget_max(n)

    def values(self):
        return self.tabs[self.tabs.active].values()

from styles import box_styles, box_style_sheet
 
class RegionBox(pn.Column):
    
    def __init__(self, project, map, budget):
        super(RegionBox, self).__init__(margin=(10,0,10,5))
        self.totals = project.totals
        self.map = map
        self.budget_box = budget
        boxes = []
        for name in project.regions:
            box = pn.widgets.Checkbox(name=name, styles=box_styles, stylesheets=[box_style_sheet])
            box.param.watch(self.cb, ['value'])
            boxes.append(box)
        self.grid = pn.GridBox(*boxes, ncols=2)
        self.selected = set()
        self.append(self.grid)

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
                b = pn.widgets.Checkbox(name=t, styles=box_styles, stylesheets=[box_style_sheet])
                lst.append(b)
                self.boxes[t] = b
            self.grid.objects.extend(lst)
        self.append(self.grid)

    def selection(self):
        return [t for t in self.boxes if self.boxes[t].value ]


class InfoBox(pn.Column):

    missing_params_text = '''### Missing Information

Please select

'''

    preview_message_text = '''### Review Optimizer Settings

Clicking Continue will run OP with the following settings:

'''

    success_text = '''### Optimization Complete

Click on the **Output** tab to see the results.
'''

    fail_text = '''### Optimization Failed

One or more OptiPass runs failed.  See the log in the Admin panel for details.
'''

    def __init__(self, template, run_cb):
        super(InfoBox, self).__init__()
        self.template = template
        self.continue_button = pn.widgets.Button(name='Continue')
        self.cancel_button = pn.widgets.Button(name='Cancel')
        self.append(pn.pane.Alert('placeholder', alert_type = 'secondary'))
        self.append(pn.Row(self.cancel_button, self.continue_button))
        self.continue_button.on_click(run_cb)
        self.cancel_button.on_click(self.cancel_cb)

    def cancel_cb(self, _):
        self.template.close_modal()
 
    def show_missing(self, rlist, bmax, tlist):
        text = self.missing_params_text
        if len(rlist) == 0:
            text += ' * one or more geographic regions\n'
        if bmax == 0:
            text += ' * a maximum budget\n'
        if len(tlist) == 0:
            text += ' * one or more targets\n'
        self[0] = pn.pane.Alert(text, alert_type = 'warning')
        self[1].visible = False
        self.template.open_modal()
        
    def show_params(self, regions, bmax, bstep, targets):
        n = bmax // bstep
        fbmax = BudgetBox.format_budget_amount(bmax)
        fbstep = BudgetBox.format_budget_amount(bstep)
        text = self.preview_message_text
        text += f'  * Regions: `{regions}`\n\n'
        text += f'  * {n} budget levels from {fbstep} up to {fbmax} in increments of {fbstep}\n\n'
        text += f'  * Targets: `{targets}`\n\n' 
        self[0] = pn.pane.Alert(text, alert_type = 'secondary')
        self[1].visible = True
        self.template.open_modal()

    def show_success(self):
        self[0] = pn.pane.Alert(self.success_text, alert_type = 'success')
        self[1].visible = False
        self.template.open_modal()

    def show_fail(self):
        self[0] = pn.pane.Alert(self.fail_text, alert_type = 'danger')
        self[1].visible = False
        self.template.open_modal()

welcome_text = '''
<h2>Welcome</h2>

<p>Click on the Start tab above to enter optimization parameters and run the optimizer.</p>
'''

placeholder_text = '''
<h2>Nothing to See Yet</h2>

<p>After running the optimizer this tab will show the results.</p>
'''

from styles import header_styles, button_style_sheet

class TideGates(pn.template.BootstrapTemplate):

    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.bf = Project('static/workbook.csv', DataSet.TNC_OR)

        self.map = TGMap(self.bf)
        self.map_pane = pn.panel(self.map.graphic())

        self.budget_box = BudgetBox()
        self.region_boxes = RegionBox(self.bf, self.map, self.budget_box)
        self.target_boxes = TargetBox(list(self.bf.target_map.keys()))
        self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=self.bf.climates, inline=False)
 
        self.optimize_button = pn.widgets.Button(name='Run Optimizer', stylesheets=[button_style_sheet])

        self.info = InfoBox(self, self.run_optimizer)

        start_tab = pn.Column(
            # pn.Row(self.info),
            self.section_head('Geographic Regions'),
            pn.WidgetBox(self.region_boxes, width=600),

            # pn.layout.VSpacer(height=5),
            self.section_head('Budget'),
            self.budget_box,

            # pn.layout.VSpacer(height=5),
            self.section_head('Targets'),
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

            self.optimize_button,
        )

        self.tabs = pn.Tabs(
            ('Home', pn.pane.HTML(welcome_text)),
            ('Start', start_tab),
            ('Output', pn.pane.HTML(placeholder_text)),
            sizing_mode = 'fixed',
            width=800,
            height=800,
        )
        
        self.sidebar.append(self.map_pane)
        self.main.append(self.tabs)        

        self.info = InfoBox(self, self.run_optimizer)
        self.modal.append(self.info)

        self.optimize_button.on_click(self.validate_settings)

    def section_head(self, s):
        return pn.pane.HTML(f'<h3>{s}</h3>', styles=header_styles)

    def validate_settings(self, _):
        regions = self.region_boxes.selection()
        budget_max, budget_delta = self.budget_box.values()
        targets = self.target_boxes.selection()

        if len(regions) == 0 or budget_max == 0 or len(targets) == 0:
            self.info.show_missing(regions, budget_max, targets)
            return
        
        self.info.show_params(regions, budget_max, budget_delta, targets)

    def run_optimizer(self, _):
        Logging.log('running optimizer')

        self.close_modal()
        self.main[0].loading = True

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
        # if base := os.environ.get('OP_OUTPUT'):
        #     self._find_output_files(base)
        #     self.op.budget_delta = budget_delta
        #     self.op.budget_max = budget_max
        # else:
            # Uncomment one of the following lines, depending on whether the progress
            # bar is displayed
            # self.op.run(self.budget_box.values(), False, self.info.update_progress)
        self.op.run(self.budget_box.values(), False)

        self.main[0].loading = False

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

    # # When debugging outside of a container define an environment variable
    # # named OP_OUTPUT, setting it to the base name of a set of existing output 
    # # files.  This helper function collects the file names so they can be
    # # used in the display

    # def _find_output_files(self, pattern):
    #     def number_part(fn):
    #         return int(re.search(r'_(\d+)\.txt$', fn).group(1))

    #     outputs = glob(f'tmp/{pattern}_*.txt')
    #     self.op.outputs = sorted(outputs, key=number_part)

    def table_click_cb(self, *events):
        # Logging.log('table cb', len(events), events[0])
        print('table click', len(events), events[0])

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

        # self.main.append(('Output', pn.panel(output, min_width=500, height=800)))
        self.tabs[2] = ('Output', output)

