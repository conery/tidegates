## Integration Tests

Integration tests are implemented in the top level application (`main.py`).

To perorm a test, run `main` with options that specify which type of test to run and where to find the data for the test.

See the documentation for `main.py` for details and examples.

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
    options:
      heading_level: 3

### TestTargets

::: src.tidegates.targets.TestTargets
    options:
      heading_level: 3

### TestOP

::: src.tidegates.optipass.TestOP
    options:
      heading_level: 3
