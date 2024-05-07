### BudgetBox

The widget that displays budget options is an instance of a class named `BudgetBox`.  It has a set of three tabs that display different options for specifying a budget:

* the default view is a slider that sets the maximum budget value; OptiPass will be run 10 times with budgets ranging from 0 up to the maximum

* an advanced view allows users to set the maximum, the interval between budgets, and the total number of budgets to consider

* the fixed view has a text entry widget there the user enters a budget, Optipass will be run once using this budget

The BudgetBox class and the three budget views are all defined in `src/budgets.py`.

::: src.tidegates.widgets.BudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 3
      filters: ""
      show_bases: false


#### BasicBudgetBox

::: src.tidegates.budgets.BasicBudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      show_bases: false

#### AdvancedBudgetBox

::: src.tidegates.budgets.AdvancedBudgetBox
    options:
      show_root_toc_entry: false
      show_docstring_attributes: true
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      show_bases: false

#### FixedBudgetBox

::: src.tidegates.budgets.FixedBudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      show_bases: false
