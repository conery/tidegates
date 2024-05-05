import param

import panel as pn
import pandas as pd

import bokeh.plotting as bk
from bokeh.io import save as savehtml
from bokeh.models.widgets.tables import NumberFormatter
from bokeh.tile_providers import get_provider
import xyzservices.providers as xyz
from bokeh.models import Range1d

from shutil import make_archive, rmtree
from pathlib import Path

from .targets import DataSet, make_layout
from .budgets import BasicBudgetBox, AdvancedBudgetBox, FixedBudgetBox
from .project import Project
from .optipass import OP
from .messages import Logging
from .styles import *

pn.extension('gridstack', 'tabulator', 'floatpanel')

class TGMap():
    """
    A TGMap object manages the display of a map that shows the locations of the barriers
    in a project.  The constructor is passed a reference to Project object that has
    barrier definitions.

    Attributes:
      map:  a Bokeh figure object, with x and y ranges defined by the locations of the barriers
      dots: a dictionary that maps region names to a list of circle glyphs for each barrier in a region
      ranges: a data frame that has the range of x and y coordinates for each region    
    """
    def __init__(self, bf):
        self.map, self.dots = self._create_map(bf)
        self.ranges = self._create_ranges(bf)

    def graphic(self):
        return self.map

    def _create_map(self, bf):
        """
        Hidden method, called by the constructor to create a Bokeh figure 
        based on the latitude and longitude of the barriers in
        a project.
        """
        self.tile_provider = get_provider(xyz.OpenStreetMap.Mapnik)
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
        p.add_tile(self.tile_provider)
        p.toolbar.autohide = True
        dots = { }
        for r in bf.regions:
            df = bf.map_info[bf.map_info.region == r]
            c = p.circle('x', 'y', size=5, color='darkslategray', source=df, tags=list(df.id))
            dots[r] = c
            c.visible = False

        self.outer_x = (bf.map_info.x.min()*0.997,bf.map_info.x.max()*1.003)
        self.outer_y = (bf.map_info.y.min()*0.997,bf.map_info.y.max()*1.003)

        return p, dots
    
    def _create_ranges(self, df):
        """
        Hidden method, called by the constructor to create a Pandas Dataframe 
        containing the range of latitudes and longitudes of the barriers in
        a project.
        """
        g = df.map_info.groupby('region')
        return pd.DataFrame({
            'x_min': g.min().x,
            'x_max': g.max().x,
            'y_min': g.min().y,
            'y_max': g.max().y,
        })

    def display_regions(self, selection):
        """
        This method is called when the user clicks the checkbox next to the name
        of a region.  Set the visible attribute of each dot to True or False depending
        on whether the region it is in is selected.

        Arguments:
          selection:  a list of names of regions currently selected
        """
        for r, dots in self.dots.items():
            dots.visible = r in selection

    def zoom(self, selection):
        """
        Update the map, setting the x and y range based on the currently selected
        regions.

        Arguments:
          selection:  a list of names of regions currently selected
        """
        if len(selection) > 0:
            xmin = min([self.ranges['x_min'][r] for r in selection])
            xmax = max([self.ranges['x_max'][r] for r in selection])
            ymin = min([self.ranges['y_min'][r] for r in selection])
            ymax = max([self.ranges['y_max'][r] for r in selection])

            mx = (xmax+xmin)/2
            my = (ymax+ymin)/2
            dx = max(5000, xmax - xmin)
            dy = max(5000, ymax - ymin)
            ar = self.map.height / self.map.width

            if dy / dx > ar:
                dx = dy / ar
            else:
                dy = dx * ar

            self.map.x_range.update(start=mx-dx/2-5000, end=mx+dx/2+5000)
            self.map.y_range.update(start=my-dy/2, end=my+dy/2)
        else:
            self.map.x_range.update(start=self.outer_x[0], end=self.outer_x[1])
            self.map.y_range.update(start=self.outer_y[0], end=self.outer_y[1])
        self.map.add_tile(self.tile_provider)

class BudgetBox(pn.Column):
    """
    There are three ways users can specify the range of budget values
    when running OptiPass.  A BudgetBox widget has one tab for each option.
    The widgets displayed inside a tab are defined by their own classes
    (BasicBudgetBox, AdvancedBudgetBox, and FixedBudgetBox).
    """

    def __init__(self):
        super(BudgetBox, self).__init__()
        self.tabs = pn.Tabs(
            ('Basic', BasicBudgetBox()),
            ('Advanced', AdvancedBudgetBox()),
            ('Fixed', FixedBudgetBox()),
        )
        self.append(self.tabs)

    def set_budget_max(self, n: int):
        """
        When the user selects or deselects a region the budget widgets need
        to know the new total cost for all the selected regions.  This method
        passes that information to each of the budget widgets.

        Arguments:
          n: the new maximum budget amount
        """
        for t in self.tabs:
            t.set_budget_max(n)

    def values(self):
        """
        Return the budget settings for the currently selected budget type.

        Returns:
          bmax:  the maximum budget to pass to OptiPass
          binc:  the increment between budget values
        """
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
        self.grid = pn.GridBox(*boxes, ncols=3)
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
        self.map.zoom(self.selected)
        if self.external_cb:
            self.external_cb()

    def selection(self):
        return self.selected
    
    def add_external_callback(self, f):
        '''Save a reference to an external function to call when a region box is clicked'''
        self.external_cb = f


class BasicTargetBox(pn.Column):

    def __init__(self, targets):
        super(BasicTargetBox, self).__init__(margin=(10,0,10,5))
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
    
    def weights(self):
        return []
    
class WeightedTargetBox(pn.Column):

    def __init__(self, targets):
        super(WeightedTargetBox, self).__init__(margin=(10,0,10,5))
        self.grid = pn.GridBox(ncols=2)
        for tnames in make_layout():
            for t in tnames:
                w = pn.Row()
                w.append(pn.widgets.TextInput(name='', placeholder='', width=25, stylesheets=[input_style_sheet]))
                w.append(t)
                self.grid.objects.append(w)
        self.append(self.grid)

    def selection(self):
        return [w[1].object for w in self.grid.objects if w[0].value]

    def weights(self):
        return [w[0].value for w in self.grid.objects if w[0].value]
    
class TargetBox(pn.Column):

    def __init__(self, targets):
        super(TargetBox, self).__init__(margin=(10,0,10,5))
        self.tabs = pn.Tabs(
            ('Basic', BasicTargetBox(targets)),
            ('Weighted', WeightedTargetBox(targets)),
        )
        self.append(self.tabs)

    def selection(self):
        return self.tabs[self.tabs.active].selection()
    
    def weights(self):
        return self.tabs[self.tabs.active].weights()

class InfoBox(pn.Column):

    missing_params_text = '''### Missing Information

Please select

'''

    invalid_weights_text = '''### Invalid Weights

Target weights must be numbers between 1 and 5 (not {})
'''

    preview_message_text = '''### Review Optimizer Settings

Clicking Continue will run the optimizer with the following settings:

'''

    success_text = '''### Optimization Complete

Click on the **Output** tab to see the results.
'''

    fail_text = '''### Optimization Failed

Reason: {}
'''

    def __init__(self, template, run_cb):
        super(InfoBox, self).__init__()
        self.template = template

        self.continue_button = pn.widgets.Button(name='Continue')
        self.continue_button.on_click(run_cb)

        self.cancel_button = pn.widgets.Button(name='Cancel')
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
        self.clear()
        self.append(pn.pane.Alert(text, alert_type = 'warning'))
        self.template.open_modal()

    def show_invalid_weights(self, w):
        text = self.invalid_weights_text.format(w)
        self.clear()
        self.append(pn.pane.Alert(text, alert_type = 'warning'))
        self.template.open_modal()
        
    def show_params(self, regions, bmax, bstep, targets, weights, climate):
        n = bmax // bstep
        fbmax = OP.format_budget_amount(bmax)
        fbstep = OP.format_budget_amount(bstep)
        text = self.preview_message_text
        text += f'  * Regions: {", ".join(regions)}\n\n'
        if n > 1:
            text += f'  * {n} budget levels from {fbstep} up to {fbmax} in increments of {fbstep}\n\n'
        else:
            text += f'  * a single budget of {fbmax}\n\n'
        targets = [t.split(':')[-1] for t in targets]
        if weights:
            targets = [f'{targets[i]} ⨉ {weights[i]}' for i in range(len(targets))]
        text += f'  * Targets: {", ".join(targets)}\n' 
        text += f'  * Climate: {climate}\n\n'
        self.clear()
        self.append(pn.pane.Alert(text, alert_type = 'secondary'))
        self.append(pn.Row(self.cancel_button, self.continue_button))
        self.template.open_modal()

    def show_success(self):
        self.clear()
        self.append(pn.pane.Alert(self.success_text, alert_type = 'success'))
        self.template.open_modal()

    def show_fail(self, reason):
        self.clear()
        text = self.fail_text.format(reason)
        if str(reason) == 'No solution':
            text += '\n * try increasing the maximum budget'
        self.append(pn.pane.Alert(text, alert_type = 'danger'))
        self.template.open_modal()

# Create an instance of the OutputPane class to store the tables and plots to
# show after running the optimizer

class OutputPane(pn.Column):

    def __init__(self, op, bf):
        super(OutputPane, self).__init__()
        self.op = op
        self.bf = bf
        # self.figures = []

        self.append(pn.pane.HTML('<h3>Optimization Complete</h3>', styles=header_styles))
        self.append(self._make_title())

        if op.budget_max > op.budget_delta:
            self.append(pn.pane.HTML('<h3>ROI Curves</h3>'))
            self.append(self._make_figures_tab())

        self.append(pn.pane.HTML('<h3>Budget Summary</h3>'))
        self.gate_count = self.op.summary.gates.apply(len).sum()
        if self.gate_count == 0:
            self.append(pn.pane.HTML('<i>No barriers selected -- consider increasing the budget</i>'))
        else:
            self.append(self._make_budget_table())
            self.append(pn.Accordion(
                ('Barrier Details', self._make_gate_table()),
                stylesheets = [accordion_style_sheet],
            ))

    def _make_title(self):
        regions = self.op.regions
        targets = [t.short for t in self.op.targets]
        if self.op.weighted:
            targets = [f'{targets[i]} ⨉ {self.op.weights[i]}' for i in range(len(targets))]
        bmax = self.op.budget_max
        binc = self.op.budget_delta
        if bmax > binc:
            title_template = '<p><b>Regions:</b> {r}; <b>Targets:</b> {t}; <b>Climate:</b> {c}; <b>Budgets:</b> {min} to {max}</p>'
            return pn.pane.HTML(title_template.format(
                r = ', '.join(regions),
                t = ', '.join(targets),
                c = self.op.climate,
                min = OP.format_budget_amount(binc),
                max = OP.format_budget_amount(bmax),
            ))
        else:
            title_template = '<p><b>Regions:</b> {r}; <b>Targets:</b> {t}; <b>Climate:</b> {c}; <b>Budget:</b> {b}'
            return pn.pane.HTML(title_template.format(
                r = ', '.join(regions),
                t = ', '.join(targets),
                c = self.op.climate,
                b = OP.format_budget_amount(bmax),
            ))
            
    def _make_figures_tab(self):
        tabs = pn.Tabs(
            tabs_location='left',
            stylesheets = [tab_style_sheet],
        )
        self.op.make_roi_curves()
        for p in self.op.display_figures:
            tabs.append(p)
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
        for i, t in enumerate(self.op.targets):
            if t.abbrev in self.op.summary.columns:
                df = pd.concat([df, self.op.summary[t.abbrev]], axis=1)
                col = t.short
                if self.op.weighted:
                    col += f'⨉{self.op.weights[i]}'
                colnames.append(col)
                formatters[col] = NumberFormatter(format='0.0', text_align='center')
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
        colnames = [c.replace('_hab','') for c in df.columns]
        if self.op.weighted:
            for i, t in enumerate(self.op.targets):
                if t.short not in colnames:             # shouldn't happen, but just in case...
                    continue
                j = colnames.index(t.short)
                colnames[j] += f'⨉{self.op.weights[i]}'
                formatters[colnames[j]] = NumberFormatter(format='0.0', text_align='center')
        df.columns = colnames

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
        if hasattr(self, 'budget_table'):
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
            b = pn.widgets.Checkbox(name=x, styles=box_styles, stylesheets=[box_style_sheet])
            if x in [self.NB, self.IT]:
                b.disabled = True
                b.value = False
            else:
                b.value = True
            self.boxes[x] = b
            self.grid.objects.append(b)

        self.filename_input = pn.widgets.TextInput(
            name = '', 
            value = self.folder_name,
        )

        self.image_type = pn.widgets.RadioBoxGroup(name='IFF', options=['HTML','PDF','PNG','JPEG'], inline=True)

        self.make_archive_button = pn.widgets.Button(name='Create Output Folder', stylesheets=[button_style_sheet])
        self.make_archive_button.on_click(self._archive_cb)

        self.append(pn.pane.HTML('<h3>Save Outputs</h3>', styles=header_styles))
        if outputs.gate_count > 0:
            self.append(pn.pane.HTML('<b>Items to Include in the Output Folder:</b>')),
            self.append(self.grid)
            self.append(pn.Row(
                pn.pane.HTML('<b>Image File Format:</b>'),
                self.image_type,
                margin=(20,0,0,0),
            ))
            self.append(pn.Row(
                pn.pane.HTML('<b>Output Folder Name:</b>'),
                self.filename_input,
                margin=(20,0,0,0),
            ))
            self.append(self.make_archive_button)
            self.append(pn.pane.HTML('<p>placeholder</p>', visible=False))

        # if there are figures at least one of them is an individual target, so enable
        # that option; if there is a net benefit figure it's the first figure, enable it
        # if it's there

        if len(outputs.op.display_figures) > 0:
            if outputs.op.display_figures[0][0] == 'Net':
                self.boxes[self.NB].value = True
                self.boxes[self.NB].disabled = False
            self.boxes[self.IT].value = True
            self.boxes[self.IT].disabled = False

    def _make_folder_name(self):
        parts = [s[:3] for s in self.outputs.op.regions]
        lst = [t.abbrev for t in self.outputs.op.targets]
        if self.outputs.op.weighted:
            lst = [f'{lst[i]}x{self.outputs.op.weights[i]}' for i in range(len(lst))]
        parts.extend(lst)
        parts.append(OP.format_budget_amount(self.outputs.op.budget_max)[1:])
        if any(t.infra for t in self.outputs.op.targets):
            parts.append(self.outputs.op.climate[0])
        return '_'.join(parts)

    def _archive_cb(self, e):
        if not any([x.value for x in self.boxes.values()]):
            return
        self.loading = True
        base = self._make_archive_dir()
        self._save_files(base)
        p = make_archive(base, 'zip', base)
        self.loading = False
        self[-1] = pn.widgets.FileDownload(file=p, filename=self.filename+'.zip', stylesheets=[button_style_sheet])

    def _make_archive_dir(self):
        self.filename = self.filename_input.value_input or self.filename_input.value
        archive_dir = Path.cwd() / 'tmp' / self.filename
        if Path.exists(archive_dir):
            rmtree(archive_dir)
        Path.mkdir(archive_dir)
        return archive_dir

    def _save_files(self, loc):
        figures = self.outputs.op.display_figures if self.image_type.value == 'HTML' else self.outputs.op.download_figures
        for name, fig in figures:
            if name == 'Net' and not self.boxes[self.NB].value:
                continue
            if name != 'Net' and not self.boxes[self.IT].value:
                continue
            if self.image_type.value == 'HTML':
                savehtml(fig, filename=loc/f'{name}.html')
            else:
                ext = self.image_type.value.lower()
                fn = loc/f'{name}.{ext}'
                fig.savefig(fn, bbox_inches='tight')
        if self.boxes[self.BS].value:
            df = self.outputs.budget_table.drop(['gates'], axis=1)
            df.to_csv(
                loc/'budget_summary.csv', 
                index=False,
                float_format=lambda n: round(n,2)
            )
        if self.boxes[self.BD].value:
            self.outputs.gate_table.to_csv(
                loc/'barrier_details.csv',
                index=False,
                float_format=lambda n: round(n,2)
            )

class TideGates(pn.template.BootstrapTemplate):

    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.bf = Project('static/workbook.csv', DataSet.TNC_OR)

        self.map = TGMap(self.bf)
        self.map_pane = pn.panel(self.map.graphic())

        self.budget_box = BudgetBox()
        self.region_boxes = RegionBox(self.bf, self.map, self.budget_box)
        self.target_boxes = TargetBox(list(self.bf.target_map.keys()))
        self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=self.bf.climates)
 
        self.optimize_button = pn.widgets.Button(name='Run Optimizer', stylesheets=[button_style_sheet])

        self.info = InfoBox(self, self.run_optimizer)

        self.map_help_button = pn.widgets.Button(name='ℹ️', stylesheets = [help_button_style_sheet])
        self.map_help_button.on_click(self.map_help_cb)

        self.region_help_button = pn.widgets.Button(name='ℹ️', stylesheets = [help_button_style_sheet])
        self.region_help_button.on_click(self.region_help_cb)

        self.budget_help_button = pn.widgets.Button(name='ℹ️', stylesheets = [help_button_style_sheet])
        self.budget_help_button.on_click(self.budget_help_cb)

        self.target_help_button = pn.widgets.Button(name='ℹ️', stylesheets = [help_button_style_sheet])
        self.target_help_button.on_click(self.target_help_cb)

        self.climate_help_button = pn.widgets.Button(name='ℹ️', stylesheets = [help_button_style_sheet])
        self.climate_help_button.on_click(self.climate_help_cb)

        welcome_tab = pn.Column(
            self.section_head('Welcome'),
            pn.pane.HTML(open('static/welcome.html').read()),
        )

        help_tab = pn.Column(
            self.section_head('Instructions'),
            pn.pane.HTML(open('static/help1.html').read()),
            pn.pane.PNG('static/ROI.png', width=400),
            pn.pane.HTML(open('static/help2.html').read()),
        )

        start_tab = pn.Column(
            # pn.Row(self.info),
            self.section_head('Geographic Regions', self.region_help_button),
            pn.WidgetBox(self.region_boxes, width=600),

            # pn.layout.VSpacer(height=5),
            self.section_head('Budget', self.budget_help_button),
            self.budget_box,

            # pn.layout.VSpacer(height=5),
            self.section_head('Targets', self.target_help_button),
            pn.WidgetBox(
                pn.Row(
                    self.target_boxes,
                    # pn.layout.HSpacer(width=10),
                    pn.Column(
                        # pn.Row(self.climate_help_button,pn.widgets.StaticText(value='<b>Climate Scenario</b>')),
                        self.section_head('Climate', self.climate_help_button),
                        self.climate_group, 
                        margin=(0,0,0,20),
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
            # height=700,
        )
        
        self.sidebar.append(pn.Row(self.map_pane, self.map_help_button))
        self.main.append(self.tabs)

        self.info = InfoBox(self, self.run_optimizer)
        self.modal.append(self.info)

        self.optimize_button.on_click(self.validate_settings)

    def section_head(self, s, b = None):
        header = pn.pane.HTML(f'<h3>{s}</h3>', styles=header_styles)
        return header if b is None else pn.Row(header, b)

    def validate_settings(self, _):
        regions = self.region_boxes.selection()
        budget_max, budget_delta = self.budget_box.values()
        targets = self.target_boxes.selection()

        if len(regions) == 0 or budget_max == 0 or len(targets) == 0:
            self.info.show_missing(regions, budget_max, targets)
            return
        
        if weights := self.target_boxes.weights():
            if not all([w.isdigit() and (1 <= int(w) <= 5) for w in weights]):
                self.info.show_invalid_weights(weights)
                return

        self.info.show_params(regions, budget_max, budget_delta, targets, weights, self.climate_group.value)

    def run_optimizer(self, _):
        Logging.log('running optimizer')

        self.close_modal()
        self.main[0].loading = True

        budget_max, budget_delta = self.budget_box.values()
        num_budgets = budget_max // budget_delta

        self.op = OP(
            self.bf, 
            list(self.region_boxes.selection()),
            [self.bf.target_map[t] for t in self.target_boxes.selection()],
            self.target_boxes.weights(),
            self.climate_group.value,
        )
        self.op.generate_input_frame()
        self.op.run(self.budget_box.values(), False)

        self.main[0].loading = False

        # If OP ran successfully we expect to find one file for each budget level 
        # plus one more for the $0 budget

        try:
            Logging.log('runs complete')
            if self.op.outputs is None or len(self.op.outputs) != num_budgets+1:
                raise(RuntimeError('Missing output files'))
            self.op.collect_results(False)
            Logging.log('Output files:' + ','.join(self.op.outputs))
            self.info.show_success()
            self.add_output_pane()
        except RuntimeError as err:
            print(err)
            self.info.show_fail(err)

    # After running OptiPass call this method to add a tab to the main
    # panel to show the results.

    def add_output_pane(self, op=None):
        op = op or self.op

        output = OutputPane(op, self.bf)
        output.make_dots(self.map.graphic())
        self.region_boxes.add_external_callback(output.hide_dots)

        self.tabs[3] = ('Output', output)

        self.tabs[4] = ('Download', DownloadPane(output))

    def map_help_cb(self, _):
        msg = pn.pane.HTML('''
        <p>When you move your mouse over the map the cursor will change to a "crosshairs" symbol and a set of buttons will appear below the map.
        Navigating with the map is similar to using Google maps or other online maps:</p>
        <ul>
            <li>Left-click and drag to pan (move left and right or up and down).</li>
            <li>If you want to zoom in and out, first click the magnifying glass button below the map; then you can zoom in and out using the scroll wheel on your mouse.</li>   
            <li>Click the refresh button to restore the map to its original size and location.</li>
        </ul>
        ''')
        self.tabs[0].append(pn.layout.FloatPanel(msg, name='Map Controls', contained=False, position='center', width=400))
    
    def region_help_cb(self, _):
        msg = pn.pane.HTML('''
        <p>Select a region by clicking in the box to the left of an estuary name.</p>
        <p>Each time you click in a box the map will be updated to show the positions of the barriers that are in our database for the estuary.</p>
        <p>You must select at least one region before you run the optimizer.</p>
        ''')
        self.tabs[2].append(pn.layout.FloatPanel(msg, name='Geographic Regions', contained=False, position='center', width=400))
    
    def budget_help_cb(self, _):
        msg = pn.pane.HTML('''
        <p>There are three ways to specify the budgets used by the optimizer.</p>
        <H4>Basic</H4>
        <p>The simplest method is to specify an upper limit by moving the slider back and forth.  When you use this method, the optimizer will run 10 times, ending at the value you select with the slider.  For example, if you set the slider at $10M (the abbreviation for $10 million), the optimizer will make ROI curves based on budgets of $1M, $2M, <i>etc</i>, up to the maximum of $10M.</p>
        <p>Note that the slider is disabled until you select one or more regions.  That's because the maximum value depends on the costs of the gates in each region.
        For example, the total cost of all gates in the Coquille region is $11.8M.  Once you choose that region, you can move the budget slider
        left and right to pick a maximum budget for the optimizer to consider.
        <H4>Advanced</H4>
        <p>If you click on the Advanced tab in this section you will see ways to specify the budget interval and the number of budgets.</p>
        <p>You can use this method if you want more control over the layout of the ROI curves, for example you can include more points by increasing the number of budgets.</p>
        <H4>Fixed</H4>
        <p>If you know exactly how much money you have to spend you can enter that amount by clicking on the Fixed tab and entering the budget amount.</p>
        <p>The optimizer will run just once, using that budget.  The output will have tables showing the gates identified by the optimizer, but there will be no ROI curve.</p>
        <p>When entering values, you can write the full amount, with or without commas (<i>e.g.</i>11,500,000 or 11500000) or use the abbreviated form (11.5M).</p>
        ''')
        self.tabs[2].append(pn.layout.FloatPanel(msg, name='Budget Levels', contained=False, position='center', width=400))
    
    def target_help_cb(self, _):
        msg = pn.pane.HTML('''
        <p>Click boxes next to one or more target names to have the optimizer include those targets in its calculations.</p>
        <p>The optimizer will create an ROI curve for each target selected. </p>
        <p>If more than one target is selected the optimizer will also generate an overall "net benefit" curve based on considering all targets at the same time.</p>
        ''')
        self.tabs[2].append(pn.layout.FloatPanel(msg, name='Targets', contained=False, position='center', width=400))
    
    def climate_help_cb(self, _):
        msg = pn.pane.HTML('''
        <p>By default the optimizer uses current water levels when computing potential benefits.  Click the button next to <b>Future</b> to have it use water levels expected due to climate change.</p>
        <p>The future scenario uses two projected water levels, both for the period to 2100. For fish habitat targets, the future water level is based on projected sea level rise of 5.0 feet.  For agriculture and infrastructure targets, the future water level is projected to be 7.2 feet, which includes sea level rise and the probabilities of extreme water levels causing flooding events.</p>
        ''')
        self.tabs[2].append(pn.layout.FloatPanel(msg, name='Targets', contained=False, position='center', width=400))