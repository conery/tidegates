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
