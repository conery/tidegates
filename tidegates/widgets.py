import param

import panel as pn
import pandas as pd

import bokeh.plotting as bk
from bokeh.io import export_png
from bokeh.models.widgets.tables import NumberFormatter
from bokeh.tile_providers import get_provider
import xyzservices.providers as xyz

from shutil import make_archive, rmtree
from pathlib import Path

from targets import DataSet, make_layout
from budgets import BasicBudgetBox, AdvancedBudgetBox, FixedBudgetBox
from project import Project
from optipass import OP
from messages import Logging
from styles import *

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
            dots[r] = c
            c.visible = False
        return p, dots

    def display_regions(self, lst):
        for r, dots in self.dots.items():
            dots.visible = r in lst


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
        self.external_cb = None
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
        if self.external_cb:
            self.external_cb()
        print(self.map.map.x_range, self.map.map.y_range)

    def selection(self):
        return self.selected
    
    def add_external_callback(self, f):
        '''Save a reference to an external function to call when a region box is clicked'''
        self.external_cb = f


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

Clicking Continue will run OptiPass with the following settings:

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
        self.continue_button.on_click(run_cb)

        self.cancel_button = pn.widgets.Button(name='Cancel')
        self.cancel_button.on_click(self.cancel_cb)

        # self.append(pn.pane.Alert('placeholder', alert_type = 'secondary'))
        # self.append(pn.Row(self.cancel_button, self.continue_button))

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
        self.clear()
        self.append(pn.pane.Alert(text, alert_type = 'warning'))
        # self[0] = pn.pane.Alert(text, alert_type = 'warning')
        # self[1].visible = False
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
        self.clear()
        self.append(pn.pane.Alert(text, alert_type = 'secondary'))
        self.append(pn.Row(self.cancel_button, self.continue_button))
        # self[0] = pn.pane.Alert(text, alert_type = 'secondary')
        # self[1].visible = True
        self.template.open_modal()

    def show_success(self):
        self.clear()
        self.append(pn.pane.Alert(self.success_text, alert_type = 'success'))
        # self[0] = pn.pane.Alert(self.success_text, alert_type = 'success')
        # self[1].visible = False
        self.template.open_modal()

    def show_fail(self):
        self.clear()
        self.append(pn.pane.Alert(self.fail_text, alert_type = 'danger'))
        # self[0] = pn.pane.Alert(self.fail_text, alert_type = 'danger')
        # self[1].visible = False
        self.template.open_modal()

# Create an instance of the OutputPane class to store the tables and plots to
# show after running the optimizer

class OutputPane(pn.Column):

    def __init__(self, op, bf):
        super(OutputPane, self).__init__()
        self.op = op
        self.bf = bf
        self.figures = None    # will be set to list of plots by _make_figures

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
        self.figures = []
        tabs = pn.Tabs(
            tabs_location='left',
            stylesheets = [tab_style_sheet],
        )
        for p in self.op.roi_curves(self.op.budget_max, self.op.budget_delta):
            tabs.append(p)
            self.figures.append(p[1])
        return tabs
    
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

    def hide_dots(self):
        if self.selected_row:
            self.dots[self.selected_row].visible = False
        self.selected_row = None

class DownloadPane(pn.Column):

    NB = 'Net benefit plot'
    IT = 'Individual target plots'
    BS = 'Budget summary table'
    BD = 'Barrier detail table'

    def __init__(self, outputs):
        super(DownloadPane, self).__init__()
        self.outputs = outputs
        self.folder_name = self._make_folder_name()

        self.grid = pn.GridBox(ncols=2)
        self.boxes = { }
        for x in [self.NB, self.BS, self.IT, self.BD]:
            b = pn.widgets.Checkbox(name=x, styles=box_styles, stylesheets=[box_style_sheet], value=True)
            self.boxes[x] = b
            self.grid.objects.append(b)

        self.filename_input = pn.widgets.TextInput(
            name = 'Archive Folder Name', 
            value = self.folder_name,
        )

        self.make_archive_button = pn.widgets.Button(name='Create Archive', stylesheets=[button_style_sheet])
        self.make_archive_button.on_click(self._archive_cb)

        self.append(pn.pane.HTML('<h3>Save Outputs</h3>', styles=header_styles))
        self.append(self.grid)
        self.append(self.filename_input)
        self.append(self.make_archive_button)
        self.append(pn.pane.HTML('<p>placeholder</p>', visible=False))

    def _make_folder_name(self):
        parts = [s[:3] for s in self.outputs.op.regions]
        parts.extend([t.abbrev for t in self.outputs.op.targets])
        parts.append(OP.format_budget_amount(self.outputs.op.budget_max)[1:])
        return '_'.join(parts)

    def _archive_cb(self, e):
        if not any([x.value for x in self.boxes.values()]):
            return
        self.loading = True
        base = self._make_archive_dir()
        self._save_files(base)
        p = make_archive(base, 'zip', base)
        self.loading = False
        self[-1] = pn.widgets.FileDownload(file=p, filename=self.filename+'.zip')

    def _make_archive_dir(self):
        self.filename = self.filename_input.value_input or self.filename_input.value
        archive_dir = Path.cwd() / 'tmp' / self.filename
        if Path.exists(archive_dir):
            rmtree(archive_dir)
        Path.mkdir(archive_dir)
        return archive_dir

    def _save_files(self, loc):
        if self.outputs.figures:
            if self.boxes[self.NB].value:
                export_png(self.outputs.figures[0], filename=loc/'net.png')
                # print(self.NB)
            if self.boxes[self.IT].value:
                for i in range(len(self.outputs.figures)-1):
                    fn = self.outputs.op.targets[i].abbrev + '.png'
                    export_png(self.outputs.figures[i+1], filename=loc/fn)
                # print(self.IT)
        if self.boxes[self.BS].value:
            df = self.outputs.budget_table.drop(['gates'], axis=1)
            df.to_csv(
                loc/'budget_table.csv', 
                index=False,
                float_format=lambda n: round(n,2)
            )
            # print(self.BS)
        if self.boxes[self.BD].value:
            self.outputs.gate_table.to_csv(
                loc/'gate_table.csv',
                index=False,
                float_format=lambda n: round(n,2)
            )
            # print(self.BD)

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

        welcome_tab = pn.Column(
            self.section_head('Welcome'),
            pn.pane.HTML(open('static/welcome.html').read()),
        )

        help_tab = pn.Column(
            self.section_head('Instructions'),
            pn.pane.HTML(open('static/help.html').read()),
        )

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

        output_tab = pn.Column(
            self.section_head('Nothing to See Yet'),
            pn.pane.HTML('<p>After running the optimizer this tab will show the results.</p>')
        )

        download_tab = pn.Column(
            self.section_head('Nothing to Download Yet'),
            pn.pane.HTML('<p>After running the optimizer use this tab to save the results.</p>')        )

        self.tabs = pn.Tabs(
            ('Home', welcome_tab),
            ('Help', help_tab),
            ('Start', start_tab),
            ('Output', output_tab),
            ('Download', download_tab),
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
            self.info.show_success()
            Logging.log('runs complete')
            self.op.collect_results(False)
            Logging.log('Output files:' + ','.join(self.op.outputs))
            self.add_output_pane()
        else:
            self.info.show_fail()

    # After running OptiPass call this method to add a tab to the main
    # panel to show the results.

    def add_output_pane(self, op=None):
        op = op or self.op

        output = OutputPane(op, self.bf)
        output.make_dots(self.map.graphic())
        self.region_boxes.add_external_callback(output.hide_dots)

        self.tabs[2] = ('Output', output)

        self.tabs[3] = ('Download', DownloadPane(output))
