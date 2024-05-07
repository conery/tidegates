
## Widget Classes

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

