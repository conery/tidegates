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
