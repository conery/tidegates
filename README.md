# Tide Gate Optimization Tool

The code in this repository is a web interface to the Tide Gate Optimization Tool.  It uses [Panel](https://panel.holoviz.org/) to display a GUI where users can enter optimization parameters -- estuaries they are interested in, a range of costs to consider, and the types of benefits they hope to achieve.   

### Installing the Server?  Read This First

The code for this web app is written entirely in Python and is open source.  Instructions for how to install and run the app can be found below.  

Before you get to that section, however, there are some important things to know about [OptiPass](https://www.ecotelligence.net/home/optipass), the program we use for computing optimal gate selections.

- OptiPass is free to use for non-commercial purposes, but for other uses a commercial license is required.
- OptiPass comes with its own GUI, but the server runs a command line version of OptiPass.  Since OptiPass is a Windows application, the server either has to be a Windows system, or it has to use Wine to run OptiPass on a Linux or macOS system. 
- We do not include an executable binary for OptiPass in this repo; if you want to set up your own server you will have to obtain a copy of the command line version of OptiPass from the developer ([Ecotelligence LLC](https://www.ecotelligence.net/)).

We have deployed the server on a Windows VM at Amazon Cloud Services.  More information on how we set up our server can be found below in the sections on installing and running the server.

Another way to deploy the server is to use our Docker image.  Based on Ubuntu, it includes Wine so it can run OptiPass.  We don't recommend this approach, however, since OptiPass runs much more slowly than it does on a Windows host.  Details about how to launch a container so it can find the OptiPass binary on the host system are also described below.

### Configuring a Server for Other Geographical Regions

The tide gate data used by the web app is in a CSV file that is included in the repository.  Once you obtain a copy of OptiPass and follow all of the other installation steps you will be ready to run optimizations using data from estuaries on the Oregon coast.

Adapting this web app to work for other regions is mainly a matter of creating a new CSV file.  Each record in this file has the location, estimated replacement cost, and potential benefits for a single tide gate or other barrier.  

However there are other things that need to be configured, as well.  Details on the format of the CSV file and the other configuration steps are described in the **Configuration** section of the technical documentation.

## Downloading and Installing the Web App



## Using the Tidegates App

## Technical Documentation



