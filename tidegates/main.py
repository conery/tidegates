import panel as pn

from widgets import TideGates

pn.extension(sizing_mode = 'stretch_width')
pn.config.css_files = ['static/tgo.css']

def make_app():
    template = pn.template.BootstrapTemplate(title='Tide Gate Optimization')
    tg = TideGates()
    template.sidebar.append(tg.map_pane)
    template.main.append(tg.main)
    return template

# template.servable()

pn.serve( 
    {'tidegates': make_app},
    port = 5006,
    admin = True,
)

