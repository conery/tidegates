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
            width=400,
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
            # c.nonselection_glyph = Circle(size=5, fill_color='darkslategray')
            # c.selection_glyph = Circle(size=8, fill_color='blue')
            dots[r] = c
            c.visible = False
        return p, dots

    def display_regions(self, lst):
        for r, dots in self.dots.items():
            dots.visible = r in lst

    # def set_selection(self, lst):
    #     self.map.select({'tag': lst[0]})


class BudgetBox(pn.Column):

    def __init__(self):
        super(BudgetBox, self).__init__()
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
        fbmax = OP.format_budget_amount(bmax)
        fbstep = OP.format_budget_amount(bstep)
        text = self.preview_message_text
        text += f'  * Regions: `{regions}`\n\n'
        if n > 1:
            text += f'  * {n} budget levels from {fbstep} up to {fbmax} in increments of {fbstep}\n\n'
        else:
            text += f'  * a single budget of {fbmax}\n\n'
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

# Create an instance of the OutputPane class to store the tables and plots to
# show after running the optimizer

from styles import accordion_style_sheet, tab_style_sheet

class OutputPane(pn.Column):

    def __init__(self, op, bf):
        super(OutputPane, self).__init__()
        self.op = op
        self.bf = bf
        self.append(pn.pane.HTML('<h3>Optimization Complete</h3>'))
        self.append(self._make_title())

        if op.budget_max > op.budget_delta:
            self.append(pn.pane.HTML('<h3>ROI Curves</h3>'))
            self.append(self._make_figures())

        self.append(pn.pane.HTML('<h3>Budget Summary</h3>'))
        self.append(self._make_budget_table())
        # pn.pane.HTML('<h3>Barrier Details</h3>'),
        # self._make_gate_table(op),
        self.append(pn.Accordion(
            ('Barrier Details', self._make_gate_table()),
            stylesheets = [accordion_style_sheet],
        ))
    
    def _make_title(self):
        regions = self.op.regions
        targets = [t.short for t in self.op.targets]
        bmax = self.op.budget_max
        binc = self.op.budget_delta
        if bmax > binc:
            title_template = '<p><b>Regions:</b> {r}; <b>Targets:</b> {t}; <b>Budgets:</b> {min} to {max}</p>'
            # n = bmax // binc
            return pn.pane.HTML(title_template.format(
                r = ', '.join(regions),
                t = ', '.join(targets),
                min = OP.format_budget_amount(binc),
                max = OP.format_budget_amount(bmax),
            ))
        else:
            title_template = '<p><b>Regions:</b> {r}; <b>Targets:</b> {t}; <b>Budget:</b> {b}'
            return pn.pane.HTML(title_template.format(
                r = ', '.join(regions),
                t = ', '.join(targets),
                b = OP.format_budget_amount(bmax),
            ))
            
    def _make_figures(self):
        figures = pn.Tabs(
            tabs_location='left',
            stylesheets = [tab_style_sheet],
        )
        for p in self.op.roi_curves(self.op.budget_max, self.op.budget_delta):
            figures.append(p)
        return figures
    
    def _make_budget_table(self):
        df = self.op.summary[['budget','habitat', 'gates']]
        colnames = ['Budget', 'Net Gain', 'gates']
        formatters = { 
            'Budget': {'type': 'money', 'symbol': '$', 'precision': 0},
            'Net Gain': NumberFormatter(format='0.0', text_align='center'),
        }
        alignment = { 
            'Budget': 'right',
            'Net Gain': 'center',
        }
        df = pd.concat([
            df,
            pd.Series(self.op.summary.gates.apply(len))
        ], axis=1)
        colnames.append('# Barriers')
        alignment['# Barriers'] = 'center'
        for t in self.op.targets:
            if t.abbrev in self.op.summary.columns:
                df = pd.concat([df, self.op.summary[t.abbrev]], axis=1)
                colnames.append(t.short)
                formatters[t.short] = NumberFormatter(format='0.0', text_align='center')
        df.columns = colnames
        table = pn.widgets.Tabulator(
            df,
            show_index = False,
            hidden_columns = ['gates'],
            editors = { c: None for c in colnames },
            text_align = alignment,
            header_align = {c: 'center' for c in colnames},
            formatters = formatters,
            selectable = True,
            configuration = {'columnDefaults': {'headerSort': False}},
        )
        table.on_click(self.budget_table_cb)
        self.budget_table = df
        return table

    def _make_gate_table(self):
        formatters = { }
        alignment = { }
        df = self.op.table_view()
        hidden = ['Count']
        for col in df.columns:
            if col.startswith('$') or col in ['Primary','Dominant']:
                formatters[col] = {'type': 'tickCross', 'crossElement': ''}
                alignment[col] = 'center'
            elif col.endswith('hab'):
                c = col.replace('_hab','')
                formatters[c] = NumberFormatter(format='0.0', text_align='center')
                # alignment[c] = 'center'
            elif col.endswith('tude'):
                formatters[col] = NumberFormatter(format='0.00', text_align='center')
                # alignment[col] = 'right'
            elif col.endswith('gain'):
                hidden.append(col)
            elif col == 'Cost':
                formatters[col] = {'type': 'money', 'symbol': '$', 'precision': 0}
                alignment[col] = 'right'
        df.columns = [c.replace('_hab','') for c in df.columns]
        table = pn.widgets.Tabulator(
            df, 
            show_index=False, 
            frozen_columns=['ID'],
            hidden_columns=hidden,
            formatters=formatters,
            text_align=alignment,
            configuration={'columnDefaults': {'headerSort': False}},
            header_align={c: 'center' for c in df.columns},
            selectable = False,
        )
        table.disabled = True
        self.gate_table = df
        return table
    
    def make_dots(self, plot):
        self.selected_row = None
        self.dots = []
        for row in self.budget_table.itertuples():
            df = self.bf.map_info[self.bf.data.BARID.isin(row.gates)]
            c = plot.circle_dot('x', 'y', size=12, line_color='blue', fill_color='white', source=df)
            # c = plot.star_dot('x', 'y', size=20, line_color='blue', fill_color='white', source=df)
            # c = plot.star('x', 'y', size=12, color='blue', source=df)
            # c = plot.hex('x', 'y', size=12, color='green', source=df)
            c.visible = False
            self.dots.append(c)

    def budget_table_cb(self, e):
        if n := self.selected_row:
            self.dots[n].visible = False
        self.selected_row = e.row
        self.dots[self.selected_row].visible = True

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


    # After running OptiPass call this method to add a tab to the main
    # panel to show the results.

    def add_output_pane(self, op=None):
        op = op or self.op
        pane = OutputPane(op, self.bf)
        pane.make_dots(self.map.graphic())
        self.tabs[2] = ('Output', pane)
