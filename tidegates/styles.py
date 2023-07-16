#
# CSS styles for widgets
#

header_styles = {
    'color': '#3171B0',
    'font-family': 'Roboto, Arial, Helvetica, sans-serif',
    'font-size': '1.2em',
    'font-weight': '600',
    'margin-top': '0px',
    'margin-bottom': '0px',
    'padding-top': '10px',
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

button_style_sheet = ''':host(.solid) .bk-btn
{
    margin-top:  20px;
    margin-left: 150px;
    font-weight: 600;
    font-size: 1.1em;
    color: #3171B0;
    padding: 10px;
    border: 2px solid #3171B0;
    border-radius: 5px;
}
'''

accordion_style_sheet = ''':host(.solid) .bk-panel-models-layout-Card.accordion
{
    background-color: white;
    border: 0px;
}
'''
