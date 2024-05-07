# Tide Gate Optimization Tool

The code in this repository is a web interface to the Tide Gate Optimization Tool.  
It is written entirely in Python, using [Panel](https://panel.holoviz.org/) to display a GUI where users can enter optimization parameters, run the optimization, and view the results.

## Documentation

The complete documentation is at [Tide Gate Optimization](https://conery.github.io/tidegates/).
It has
* instructions on how to use the app
* installation and configuration instructions for administrators who want to run the app
* technical documentation of the source code

### Installing the Server?  Read This First

The web app runs an application named [OptiPass](https://www.ecotelligence.net/home/optipass) to carry out the optimizations.

- OptiPass is free to use for non-commercial purposes, but for other uses a commercial license is required.
- OptiPass comes with its own GUI, but the server runs a command line version of OptiPass.  Since OptiPass is a Windows application, the server either has to be a Windows system, or it has to use Wine to run OptiPass on a Linux or macOS system. 
- We do not include an executable binary for OptiPass in this repo; if you want to set up your own server you will have to obtain a copy of the command line version of OptiPass from the developer ([Ecotelligence LLC](https://www.ecotelligence.net/)).

We have deployed the server on a Windows VM at Amazon Cloud Services.  More information on how we set up our server can be found in the documentation sections on installing and running the server.

Another way to deploy the server is to use our Docker image.  Based on Ubuntu, it includes Wine so it can run OptiPass.  We don't recommend this approach, however, since OptiPass runs much more slowly than it does on a Windows host.  Details about how to launch a container so it can find the OptiPass binary on the host system are also described in the documentation.


