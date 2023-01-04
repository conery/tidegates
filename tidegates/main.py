import panel as pn

from widgets import TideGates

pn.extension(sizing_mode = 'stretch_width')

template = pn.template.BootstrapTemplate(title='Tide Gate Optimization')
pn.config.css_files = ['static/tgo.css']

tg = TideGates()
template.sidebar.append(tg.map_pane)
template.main.append(tg.main)

template.servable()
