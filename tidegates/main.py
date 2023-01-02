import panel as pn

# from jinja2 import Environment, FileSystemLoader
# env = Environment(loader=FileSystemLoader('./templates'))

pn.extension(sizing_mode = 'stretch_width')

template = pn.template.BootstrapTemplate(title='Tide Gate Optimization')
pn.config.css_files = ['static/tgo.css']

from widgets import TideGates

tg = TideGates()

# app = pn.Row(
#     tg.map_pane, 
#     pn.Spacer(width=10),
#     tg.main,
#     sizing_mode='stretch_both'
# )

# template.main.append(app)

template.sidebar.append(tg.map_pane)
template.main.append(tg.main)

template.servable()
