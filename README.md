# Tide Gate Optimization Tool
Estuaries are important transition zones between freshwater and marine ecosystems, providing essential habitat for both resident and migratory species.  Salmon, lamprey, and other aquatic species need to access streams and floodplains that are vital for their foraging, spawning, refuge, and rest.

For more than 100 years residents of the Oregon coast have created tide gates, levees, and other barriers to help control the tide and protect farm land, roads, building, and other infrastructure.  Many of the tide gates are failing and should be replaced with modern designs that meet current fish passage regulations.

The **Tide Gate Optimization Tool** is a decision support system that helps landowners and other stakeholders balance the potential gain in benefits against the costs necessary to achieve those benefits. 

## Web Application

The code in this repository is a web application built with [Panel](https://panel.holoviz.org/).  Users enter parameters -- which estuaries they are interested in, a range of costs to consider, and the benefits they hope to achieve -- using a GUI displayed in their web browser.   

![](static/start_screenshot.png)

The GUI passes that information to the server, which runs the optimization algorithm.  The output is displayed in the GUI in the form of ROI curves and tables with detailed information about the tide gates included in the optimal solution.

![](static/result_screenshot.png)

### Installing the Server?  Read This First

The code for this web app is written entirely in Python and is open source.  Instructions for how to install and run the app can be found below.  Before you get to that section, however, there are some important things to know about [OptiPass](https://www.ecotelligence.net/home/optipass), the program we use for computing optimal gate selections.

- OptiPass is free to use for non-commercial purposes, but for other uses a commercial license is required.

- We do not include an executable binary for OptiPass in this repo; if you want to set up your own server you will have to obtain a copy from the developer ([Ecotelligence LLC](https://www.ecotelligence.net/)).
- OptiPass comes with its own GUI, but the server runs a command line version of OptiPass.  Since OptiPass is a Windows application, the server either has to be a Windows system, or it has to use Wine to run OptiPass on a Linux or macOS system.  We strongly recommend the former, but if you want to use Wine there is a section in the technical documentation that explains how to configure the system to do it.

### Configuring a Server for Other Geographical Regions

The tide gate data used by the web app is in a CSV file that is included in the repository.  Once you obtain a copy of OptiPass and follow all of the other installation steps you will be ready to run optimizations using data from estuaries on the Oregon coast.

Adapting this web app to work for other regions is mainly a matter of creating a new CSV file.  Each record in this file has the location, estimated replacement cost, and potential benefits for a single tide gate or other barrier.  

However there are other things that need to be configured, as well.  The process is described in the **Configuration** section of the technical documentation.

## Acknowledgements

## Downloading and Installing the Web App

## Running the Server



