#
# Widgets to display budget options for the Tide Gate Optimization tool
#

import panel as pn
import param
from bokeh.models.formatters import NumeralTickFormatter

from .styles import slider_style_sheet

class BasicBudgetBox(pn.WidgetBox):
    """
    The default budget widget displays a slider that ranges from 0
    up to a maximum value based on the total cost of all barriers in
    currently selected regions.
    """

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
        """
        Choose a maximum budget by scanning a table of budget levels to
        find the first one less than the total cost.

        Arguments:
          n: the total cost of all barriers in the current selection.
        """
        for i in range(len(self.levels)-1, -1, -1):
            if n >= self.levels[i][1]:
                self.slider.options = self.labels[:i+1]
                break

    def values(self):
        """
        Return the selected budget level (based on the slider position) and
        the number of budgets.  For basic budgets the interval between budgets
        is computed by dividing the select budget value by the number of increments
        (a constant defined in the class, currently equal to 10).

        Returns:
          bmax:  the highest budget to pass to OptiPass
          binc:  the increment between budgets
        """
        x = self.map[self.slider.value]
        return x, (x // self.increments)
    
class FixedBudgetBox(pn.WidgetBox):
    """
    This option is for situations where a user knows exactly how much money they
    have to spend and want to know the optimal set of barriers to replace for that
    amount of money.  OptiPass is run twice -- once to determine the current 
    passabilities, and once to compute the benefit from the specified budget.
    The widget simply displays a box where the user enters the dollar amount for
    their budget.
    """

    def __init__(self):
        super(FixedBudgetBox, self).__init__(margin=(15,0,15,5))
        self.input = pn.widgets.TextInput(name='Budget Amount', value='$')
        self.append(self.input)

    def set_budget_max(self, n):
        pass

    def values(self):
        """
        Return the specified budget amount as both the maximum budget and the
        budget interval.
        """
        s = self.input.value
        if s.startswith('$'):
            s = s[1:]
        n = self.parse_dollar_amount(self.input.value)
        return n, n

    def parse_dollar_amount(self, s: str):
        """
        Make sure the sring entered by the user has an acceptable format.
        It can be all digits (e.g. "1500000"), or digits separated by commas
        (e.g. "1,500,000"), or a number followed by a K or M (e.g. "1.5M").
        There can be a dollar sign at the front of the string.

        Arguments:
          s:  the string entered into the text box

        Returns:
          the value of the string converted into an integer
    
        """
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
    """
    The "advanced" option gives the user the most control over the budget values processed
    by OptiPass by letting them specify the number of budget levels (in the basic budget
    there are always 10 budget levels).  
    
    This box has three widgets:  a slider to specify the
    maximum amount, another slider to specify the increment between budgets, and
    an input box to specify the number of budgets.  Adjusting the value of any of these
    widgets automatically updates the other two.  For example, if the maximum is set to $1M
    and the number of budgets is 10, the increment is $100K.  If the user changes the number
    of budgets to 20, the increment drops to $50K.  Or if they change the maximum to $2M, the
    increment increases to $200K.
    """

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
        """
        In this widget the maximum budget and budget increment are determined
        by the values in the corresponding widgets.
        """
        return self.max_slider.value, self.inc_slider.value

    def set_budget_max(self, n):
        """
        Called when the user selects or deselects a region.  Save the new
        maximum, and update the value of the increment based on the new maximum.

        Arguments:
          n:  the total cost of all barriers in the selected regions.
        """
        self.max_slider.end = max(1, n)
        self.max_slider.start = self.MAX_STEP
        self.inc_slider.end = max(1, n // 2)
        self.inc_slider.start = max(self.INC_STEP, n / self.COUNT_MAX)
        lim = 'N/A' if n == 0 else f'${n/1000000:.2f}M'
        self[0][1] = pn.pane.HTML(f'<b>Limit: {lim}</b>')

    def max_updated(self, e):
        """
        Callback function invoked when the user moves the maximum budget
        slider.  Computs a new budget increment.
        """
        self.inc_slider.value = self.max_slider.value // self.count_input.value

    def inc_updated(self, e):
        """
        Callback function invoked when the user changes the budget increment.
        Computes a new number of budgets.
        """
        c = max(self.COUNT_MIN, self.max_slider.value // self.inc_slider.value)
        c = min(self.COUNT_MAX, c)
        self.count_input.value = c

    def count_updated(self, e):
        """
        Callback function invoked when the user changes the number of budget
        levels.  Computes a new budget increment.
        """
        self.inc_slider.value = self.max_slider.value // self.count_input.value

