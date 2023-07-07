import sys

import panel as pn

# from widgets import TideGates
# from targets import DataSet
# from project import Project
# from optipass import OP

welcome_text = '''
<h1>Welcome</h1>
'''

map_content = '''
<h1>Map</h1>
<p>A nice view of the Oregon coast</p>
'''

map_styles = {
    'background-color': '#F6F6F6',
    'border': '2px solid black',
    'border-radius': '5px',
    'padding': '10px',
}

box_styles = {
    'padding-top': '5px',
    'padding-bottom': '5px',
}

box_style_sheet = '''input[type="checkbox" i]
{
    margin-left: 10px;       /* space to left of checkbox */
    margin-right: 5px;       /* space between checkbox and label */
}
'''

radio_style_sheet = '''input[type="radio" i]
{
    margin-right: 5px;       /* space between button and label */
}
'''

slider_style_sheet = '''.bk-input-group
{
    padding: 10px;          /* space between value and slider */
}
'''

def region_box():
    labels = ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'omega']
    boxes = [pn.widgets.Checkbox(name=x, width=100, styles=box_styles, stylesheets=[box_style_sheet]) for x in labels]
    grid = pn.GridBox(*boxes, ncols=2)
    return grid

def budget_slider():
    values = list(range(0,101,10))
    return pn.widgets.DiscreteSlider(
        options = values, 
        value = values[0],
        name = 'Maximum Budget',
        margin=(20,20,20,20),
        stylesheets=[slider_style_sheet],
    )

header_styles = {
    'color': '#3171B0',
    'font-family': 'Roboto, Arial, Helvetica, sans-serif',
    'font-size': '1.3em',
    'font-weight': '600',
    'margin-top': '0px',
    'margin-bottom': '0px',
    'padding-top': '10px',
}

def header(s):
    return pn.pane.HTML(f'<h3>{s}</h3>', styles=header_styles)

def climate_box():
    return pn.widgets.RadioBoxGroup(
        name='Climate', 
        options=['Current','Future'], 
        inline=False,
        margin=(10,20),
        stylesheets=[radio_style_sheet],
    )

class TideGates(pn.template.BootstrapTemplate):

    def __init__(self, **params):
        super(TideGates, self).__init__(**params)

        self.map_pane = pn.pane.HTML(map_content, styles=map_styles)

        self.optimize_button = pn.widgets.Button(name='Run Optimizer')
        self.continue_button = pn.widgets.Button(name='Continue')
        self.cancel_button = pn.widgets.Button(name='Cancel')

        # self.climate_group = pn.widgets.RadioBoxGroup(name='Climate', options=self.bf.climates, inline=False)
        # self.budget_box = BudgetBox()
        # self.region_boxes = RegionBox(self.bf, self.map, self.budget_box)

        # # self.target_boxes = pn.widgets.CheckBoxGroup(name='Targets', options=list(self.bf.target_map.keys()), inline=False)
        # self.target_boxes = TargetBox(list(self.bf.target_map.keys()))
 
        # self.info = InfoBox()

        start_tab = pn.Column(
            # pn.Row('<h3>Geographic Regions</h3>'),
            header('Geographic Regions'),
            pn.WidgetBox(region_box(), width=600),

            # pn.layout.VSpacer(height=5),
            # pn.Row('<h3>Budget</h3>'),
            header('Budget'),
            pn.WidgetBox(budget_slider(), width=600),

            # pn.layout.VSpacer(height=5),
            # pn.Row('<h3>Targets</h3>'),
            header('Targets'),
            pn.WidgetBox(climate_box()),

            # pn.layout.VSpacer(height=20),
            pn.Row(pn.layout.Spacer(width=200), self.optimize_button, width=600),
        )

        self.tabs = pn.Tabs(
            ('Home', pn.pane.HTML(welcome_text)),
            ('Start', start_tab),
            # sizing_mode = 'fixed',
            # width=800,
            # height=800,
        )

        self.optimize_button.on_click(self.validate_settings)
        self.continue_button.on_click(self.run_optimizer)
        self.cancel_button.on_click(self.cancel_cb)

        self.sidebar.append(self.map_pane)
        self.main.append(self.tabs)

        self.info = InfoBox()
        self.modal.append(self.info)
        self.toggle = False

    def validate_settings(self, _):
        print('optimize button clicked')
        # self.modal.append(header('¿Que?'))
        # self.modal.clear()
        # self.modal.append(header('Verify Settings'))
        # print('added title')
        # self.modal.append(pn.pane.HTML('''
        #     <p>Clicking <b>continue</b> below will run OP 10 times with the following settings</p>
        #     <ul>
        #     <li> regions ... </li>
        #     <li> targets ... </li>
        #     <li> budget levels ... </li>
        #     </ul>
        # '''
        # ))
        # print('added text')
        # self.modal.append(pn.Row(self.cancel_button, self.continue_button))
        # print('added buttons')
        # for x in self.modal:
        #     print(x)
        self.toggle = not self.toggle
        self.info.show_alert(self.toggle)
        self.open_modal()

    def run_optimizer(self, _):
        print('running optimizer...')
        self.close_modal()

    def cancel_cb(self, _):
        print('cancel')
        self.close_modal()

class InfoBox(pn.Column):

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
        self.append(pn.pane.HTML('<h3>Title</h3>'))
        self.append(pn.pane.Alert(InfoBox.success_message_text, alert_type='success'))
        self.append(pn.pane.HTML('<p>some more text...<p>'))
        self.messages = [
            self.missing_params_text,
            self.success_message_text,
            self.fail_message_text,
        ]
        self.message_num = 0

    def show_alert(self, flag):
        self[1].visible = False
        self[2] = pn.pane.HTML(self.messages[self.message_num])
        self.message_num = (self.message_num + 1) % len(self.messages)

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

def make_app():
    return TideGates(
        title='Tide Gate Optimization', 
        sidebar_width=425
    )

def start_app():
    pn.serve( 
        {'tidegates': make_app},
        port = 5007,
        verbose = True,
        autoreload = True,
    )

def test_info():
    widget = InfoBox()
    widget.show()
    return widget

if __name__ == '__main__':
    pn.extension(design='native')
    if len(sys.argv) == 1:
        start_app()
    else:
        print('Usage:  panel serve sandbox/mockup.py')
