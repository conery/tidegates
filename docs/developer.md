# Technical Documentation

This section has details on each class and top level function in the application.

The source code is in a folder named `src`.  The top level application is in `main.py`.
A module named `tidegates` has submodules for the main parts of the GUI.

```
src
├── main.py
└── tidegates
    ├── budgets.py
    ├── messages.py
    ├── optipass.py
    ├── project.py
    ├── styles.py
    ├── targets.py
    └── widgets.py
```
<br/>

## Tidegate Data Files

All of the data used by the optimizer is in a single CSV file.
The file can have data on tide gates, culverts, or any obstacle encountered by migrating fish.
We'll use the generic term "barrier."

A data file has one line for each barrier.
The attributes (columns) define a barrier's ID, the ID of it's downstream neighbor, it's geographic name (typically a river system), and the costs and benefits of restoring the barrier.

The web app looks for data files in the `static` directory.
The repo has one data file, named `test_wb.csv` created using the example river system shown in the OptiPass user manual:
```
BARID,REGION,DSID,HAB1,PRE1,POST1,HAB2,PRE2,POST2,COST
A,OPM,NA,2.1,0.4,1.0,1.68,0.6,1.0,250
B,OPM,A,0.9,0.0,1.0,0.72,0.0,1.0,120
C,OPM,B,4.3,0.3,1.0,3.44,0.45,1.0,70
D,OPM,A,1.7,0.5,NA,1.36,0.75,NA,NA
E,OPM,D,1.2,0.2,1.0,0.96,0.3,1.0,100
F,OPM,D,0.5,0.1,1.0,0.40,0.15,1.0,50
```
(the "OPM" in the REGION column stands for "OptiPass Manual").

The Python code for the web app refers to another data file, named `workbook.csv`, that is also expected to be in the `static` folder.
This file has data from over 1,000 tide gates on the Oregon coast.
It is not include in the repo.

> _Eventually the names and locations of data files will be defined in a configuration file, and all the references to these two CSV files will be replaced with values taken from the configuration file._
<br/>

## Targets

To allow for cases where a river might be home to several different species, and the fact that barriers impact the passability of those species in different ways, a data file can be multiple columns to describe habitats.
The example data shown above has two columns of habitat values, named "HAB1" and "HAB2".
The values in those columns are river miles: the total amount of water upstream from a barrier before the next barrier or the river's source.
In other cases the column might have land area upstream from a barrier, in units of acres or square miles.

For each habitat the optimizer also needs to know the current passability at a barrier and the expected passability if the barrier is replaced or updated.
The columns named "PRE1" and "POST1" are the pre- and post-restoration passabilities for "HAB1", and "PRE2" and "POST2" are the passabilites for "HAB2".

When we run OptiPass we need to tell it which habitat column(s) to use.
We can choose a single habitat by itself, or specify several habitat columns and tell the optimizer how to weight them.

The Targets module defines a data structure called a Target that contains all the information about a habitat.
There will be one Target object for each habitat.
The object will have the names of the columns in the data file that have the habitat and passability values.
It will also have names to use when the habitat is displayed in the GUI and used in output tables and plots.

The Target type is defined using Python's `namedtuple` function, which is passed the name of the type to create and the attributes each object will have:
```
Target = namedtuple('Target', ['abbrev', 'long', 'short', 'habitat', 'prepass', 'postpass', 'unscaled', 'label', 'infra'])
```

The attributes are:

* `abbrev` is a short-letter ID for a habitat
* `long` is a string that will be displayed in the GUI
* `short` is a shorter name used in plots and output tables
* `habitat` is the column in the CSV file with the habitat value (see note below)
* `prepass` is the passability before restoration
* `postpass` is passability after restoration
* `unscaled` is the actual habitat, in miles for streams or acres for infrastructure (see note below)
* `label` is a string used to label the y-axis in ROI curves
* `infra` specifies the type of target (True for infrastructure, False for streams)

This statement creates a Target object for Habitat 1 from the OptiPass Manual.
Since this data is used for testing, and doesn't show up in the GUI, several of the fields are empty.
```
Target('T1', '', 'Target 1', 'HAB1', 'PRE1', 'POST1', '', '', '')
```

Here is an example of a target definition using columns from the Oregon Coast data.
In this case we need to use the last three columns to tell the optimizer the target is not an infrastructure target:
```
Target('CO', 'Coho Streams, 'Coho', 'sCO', 'PREPASS_CO', 'POSTPASS', 'Coho_salmon', 'Habitat Potential (miles)', False),
```

**Note: Scaled Data**

Both habitats in the example data are based on river miles, but the infrastructure habitats in the Oregon Coast data are based on other units.
In order to run an optimization that combines habitat types the data file has an extra column for each habitat, containing a scaled value (for example, the "sCO" in the example above for Coho salmon refers to the scaled river miles column in that CSV file).
The original unscaled values are still in the file, but are not used by the app.

**DataSet**

An enumeration named DataSet defines IDs for the two data sets that can be used by the web app:  

* `DataSet.OPM` refers to data from the OptiPass manual
* `DataSet.TNC_OR` refers to data from the Oregon coast

### `make_targets`

::: src.tidegates.targets.make_targets
    options:
      show_root_toc_entry: false
      

## Project

::: src.tidegates.project.Project
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true

<br/>

## Widgets

The GUI displayed in a user's browser shows dozens of graphical elements.
These "widgets" include checkboxes that allow users to select geographic regions and restoration targets, sliders to specify budget levels, and buttons that run the optimizer or show help messages.

If all these widgets are defined in a single module the code will be very messy.
Instead, the web app uses a common technique:  we define our own widget classes, using inheritance so our objects are a special case of an existing type of widget.

A good example is a class named RegionBox.  Instead of having 15 separate checkboxes, one for each region in the Oregon Coast data set, we make just one object, an instance of our new RegionBox class.  We pass a Project object to the function that creates this object, and the function scans the data to find all the region names, automatically making one checkbox for each separate region. All these checkboxes are stored internally, inside the RegionBox, keeping our code nice and tidy.

The Python syntax for defining a new class that is derived from an existing class uses a `class` statement.
This is the statement that defines the RegionBox class:
```
class RegionBox(pn.Column):
    ...
```
`pn.Column` is an existing widget class, defined in the Panel library.
That means our new RegionBox objects will be special types of columns that can be inserted into the GUI at some place.

The code that is called to create a new object is a function named `__init__` defined inside the class.
The first argument to `__init__` is always `self`, which is a reference to the object being built.

Here is a simplified version of the `__init__` function for the RegionBox class (the actual definition is shown below, in the documentation for RegionBox):
```
class RegionBox(pn.Column):
    
    def __init__(self, project):
        boxes = []
        for name in project.regions:
            box = pn.widgets.Checkbox(name=name, styles=box_styles)
            box.param.watch(self.cb, ['value'])
            boxes.append(box)
        self.grid = pn.GridBox(*boxes, ncols=3)
```
When this function is called, it initializes a variable named `boxes` to be an empty list.  The `for` loop iterates over all the region names (which are part of the Project object passed to the function).  It makes a Checkbox widget for each region and adds the box to the list of boxes.  At the end of the loop all the boxes are put into a grid with three columns.

The line in the middle of the loop that calls `box.param.watch` is where all the "magic" happens.  This function call tells the GUI that whenever a checkbox is clicked it should call a function named `cb` that is also defined inside the RegionBox class.  Here is a simplified version:
```
def cb(self, event):
    r = event.obj.name
    if event.new:
        self.selected.add(r)
    else:
        self.selected.remove(r)
```
The name `cb` is short for "callback", a common name for this type of function.  The parameter named `event` has information about what the user just did.  In this case, we want to get the name of the button (which will be one of the region names) and then update the set of selected regions.  If the button was turned on we add the region name to the set, otherwise we remove it.

### BudgetBox

The widget that displays budget options is an instance of a class named `BudgetBox`, defined in `widgets.py`.  It has a set of three tabs that display different options for specifying a budget.  

::: src.tidegates.widgets.BudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 3
      filters: ""


### Budget Widgets

The widgets for the three different ways of specifying budgets are defined in their own classes, which can be found in a file named `budgets.py`.

#### BasicBudgetBox

::: src.tidegates.budgets.BasicBudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      filters: ""

#### AdvancedBudgetBox

::: src.tidegates.budgets.AdvancedBudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      filters: ""

#### FixedBudgetBox

::: src.tidegates.budgets.FixedBudgetBox
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 4
      filters: ""

### TGMap

::: src.tidegates.widgets.TGMap
    options:
      show_root_toc_entry: false
      docstring_options:
        ignore_init_summary: true
      merge_init_into_class: true
      heading_level: 3
      filters: ""

## Main

This module has the code that sets up the application and launches the Bokeh server.

### `init_cli`

Use `argparse` to define the command line arguments:

* `--action`:  a verb that defines how the app will run:
    * `generate`: used to test the code that makes the input file for OptiPass;  make the file, print it, and exit
    * `run`: used to test the code that runs OptiPass; make the input file, then create and run the shell commands that run OptiPass.exe
    * `preview`: same as `run` but just prints the shell commands instead of executing them
    * `parse`: used to test the code that parses the output from OptiPass; requires the `--output` option to specify the path to files created by OptiPass
    * `all`: used to run an integration test:  generates the input for OptiPass, runs OptiPass, parses the results, displays the plots
    * `gui`: same as `all` but puts the results in the GUI

* `--project`: path to a CSV file with barrier descriptions (default: `static/workbook.csv`)

* `--regions`: one or more region names (used to test data file generation and parsing)

**Command Line**

The application needs files in the `bin` and `static` folders of the project.
To run the application, open a terminal window and `cd` to the top level folder.
The application is in the `src` folder.
Type this command to make sure the application is installed and configured:

```
$ python3 src/main.py --help
```

**Start the Server**

To start the application simply run the program without any command line arguments:

```
$ python3 src/main.py
```

**Integration Tests**

The command line arguments allow the developer to run various integration tests.

This example tests the code that creates the input files for OptiPass by making a file for
gates in the Coos region and targets CO and CH.

```
$ python3 src/main.py --action generate --region Coos --targets CO CH --output test1
```

Test the code that makes the output panes (data tables and ROI plots) by parsing
the results of a previous run, in this case a set of files that start with the
string `tmpwok9i8rl`.  

```
$ python3 src/main.py --action parse --region Coquille --out tmpwok9i8rl 
```

**Source**

::: src.main.init_cli

### `make_app`

::: src.main.make_app

### `start_app`

::: src.main.start_app

### `validate_options`

::: src.main.validate_options

-----

## `messages.py`

::: src.tidegates.messages

## `optipass.py`

::: src.tidegates.optipass

## `styles.py`

::: src.tidegates.styles

## `widgets.py`
::: src.tidegates.widgets

## Unit Tests

If a module has unit tests they are included in the source file.
Tests are defined at the end of the file, in a class that has a name that starts with `Test`.
For example, `project.py` defines a class named Project, and at the end of the file is another class named TestProject.

A test class defines a series of static methods that have names beginning with `test`.
These methods are run in order.

To run tests for a module, open a terminal window and `cd` to the top level folder.
Then type a command that runs `pytest`, including the name of the module to test:

```
$ pytest src/tidegates/project.py 
```

It's also possible to run all the tests with a single shell command:

```
$ pytest src/tidegates/*.py
```
<br/>

### TestProject

::: src.tidegates.project.TestProject

