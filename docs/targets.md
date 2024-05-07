
## Restoration Targets

To allow for cases where a river might be home to several different species, and the fact that barriers impact the passability of those species in different ways, a data file can be multiple columns to describe habitats.
The example data shown above has two columns of habitat values, named "HAB1" and "HAB2".
The values in those columns are river miles: the total amount of water upstream from a barrier before the next barrier or the river's source.
In other cases the column might have land area upstream from a barrier, in units of acres or square miles.

For each habitat the optimizer also needs to know the current passability at a barrier and the expected passability if the barrier is replaced or updated.
The columns named "PRE1" and "POST1" are the pre- and post-restoration passabilities for "HAB1", and "PRE2" and "POST2" are the passabilites for "HAB2".

When we run OptiPass we need to tell it which habitat column(s) to use.
We can choose a single habitat by itself, or specify several habitat columns and tell the optimizer how to weight them.

### `Target`

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
      
