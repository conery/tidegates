#
# Widgets to display budget options for the Tide Gate Optimization tool
#

import panel as pn
import param
from bokeh.models.formatters import NumeralTickFormatter

# The GUI displays three ways users can specify a range of budgets when
# runnoing OptiPass.  The main budget widget is a collection of tabs,
# one for each type of budget.  

# # The BudgetBox class is an abstract base class that defines the visual
# # attributes for each view. 

# class BudgetBox(pn.WidgetBox):

#     BUDGETBOXHEIGHT = 100
#     BUDGETBOXWIDTH = 600

#     def __init__(self):
#         super(BudgetBox, self).__init__(
#             margin = (15,0,15,5),
#             height = self.BUDGETBOXHEIGHT,
#             width = self.BUDGETBOXWIDTH,
#         )

from styles import slider_style_sheet

class BasicBudgetBox(pn.WidgetBox):

    levels = [
        ('$0', 0),
        ('$500K', 500000),
        ('$1M', 1000000),
        ('$2.5M', 2500000),
        ('$5M', 5000000),
        ('$10M', 10000000),
        ('$25M', 25000000),
        ('$50M', 50000000),
        ('$100M', 100000000),
    ]

    increments = 10

    def __init__(self):
        super(BasicBudgetBox, self).__init__(margin=(15,0,15,5))
        self.labels = [ x[0] for x in self.levels ]
        self.map = { x[0]: x[1] for x in self.levels }
        self.slider = pn.widgets.DiscreteSlider(
            options = self.labels[:1], 
            value = self.labels[0],
            name = 'Maximum Budget',
            margin=(20,20,20,20),
            stylesheets=[slider_style_sheet],
        )
        self.append(self.slider)

    def set_budget_max(self, n):
        for i in range(len(self.levels)-1, -1, -1):
            if n >= self.levels[i][1]:
                self.slider.options = self.labels[:i+1]
                break

    def values(self):
        x = self.map[self.slider.value]
        return x, (x // self.increments)
    
class FixedBudgetBox(pn.WidgetBox):

    def __init__(self):
        super(FixedBudgetBox, self).__init__(margin=(15,0,15,5))
        self.input = pn.widgets.TextInput(name='Budget Amount', value='$')
        self.append(self.input)

    def set_budget_max(self, n):
        pass

    def values(self):
        s = self.input.value
        if s.startswith('$'):
            s = s[1:]
        n = self.parse_dollar_amount(self.input.value)
        return n, n

    def parse_dollar_amount(self,s):
        try:
            if s.startswith('$'):
                s = s[1:]
            if s.endswith(('K','M')):
                multiplier = 1000 if s.endswith('K') else 1000000
                res = int(float(s[:-1]) * multiplier)
            elif ',' in s:
                parts = s.split(',')
                assert len(parts[0]) <= 3 and (len(parts) == 1 or all(len(p) == 3 for p in parts[1:]))
                res = int(''.join(parts))
            else:
                res = int(s)
            return res
        except Exception:
            raise ValueError('unexpected format in dollar amount')
            
class AdvancedBudgetBox(pn.WidgetBox):

    MAX_STEP = 10000
    INC_STEP = 1000
    COUNT_MIN = 2
    COUNT_MAX = 100
    SLIDER_WIDTH = 400

    def __init__(self):
        super(AdvancedBudgetBox, self).__init__(margin=(15,0,15,5))

        self.cap = 0

        self.max_slider = pn.widgets.FloatSlider(
            name='Maximum Budget', 
            start=0, 
            end=1, 
            step=self.MAX_STEP,
            value=0,
            width=self.SLIDER_WIDTH,
            format=NumeralTickFormatter(format='$0,0'),
            stylesheets=[slider_style_sheet],
        )

        self.inc_slider = pn.widgets.FloatSlider(
            name='Budget Interval', 
            start=0, 
            end=1, 
            step=self.INC_STEP,
            value=0,
            width=self.SLIDER_WIDTH//2,
            format=NumeralTickFormatter(format='$0,0'),
            stylesheets=[slider_style_sheet],
        )

        self.count_input = pn.widgets.IntInput(
            name='Number of Budgets', 
            value=10, 
            step=1, 
            start=self.COUNT_MIN,
            end=self.COUNT_MAX,
            width=75,
        )

        self.append(pn.Row(self.max_slider, pn.pane.HTML('<b>Limit: N/A<b>')))
        self.append(pn.Row(self.inc_slider, self.count_input))

        self.max_slider.param.watch(self.max_updated, ['value'])
        self.inc_slider.param.watch(self.inc_updated, ['value'])
        self.count_input.param.watch(self.count_updated, ['value'])

    def values(self):
        return self.max_slider.value, self.inc_slider.value

    def set_budget_max(self, n):
        self.max_slider.end = max(1, n)
        self.max_slider.start = self.MAX_STEP
        self.inc_slider.end = max(1, n // 2)
        self.inc_slider.start = max(self.INC_STEP, n / self.COUNT_MAX)
        lim = 'N/A' if n == 0 else f'${n/1000000:.2f}M'
        self[0][1] = pn.pane.HTML(f'<b>Limit: {lim}</b>')

    def max_updated(self, e):
        self.inc_slider.value = self.max_slider.value // self.count_input.value

    def inc_updated(self, e):
        c = max(self.COUNT_MIN, self.max_slider.value // self.inc_slider.value)
        c = min(self.COUNT_MAX, c)
        self.count_input.value = c

    def count_updated(self, e):
        self.inc_slider.value = self.max_slider.value // self.count_input.value

