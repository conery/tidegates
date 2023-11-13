# Tide Gate Optimization
Estuaries are transition zones between freshwater and marine ecosystems, providing essential habitat for both resident and migratory species.  Salmon, lamprey, and other species need to access streams and floodplains that are vital for their foraging, spawning, refuge, and rest.

For more than 100 years residents of the Oregon coast have created tide gates, levees, and other barriers to help control the tide and protect farm land, roads, building, and other infrastructure.  Many of the tide gates are failing and should be replaced with modern designs that meet current fish passage regulations.

The Nature Conservancy has developed a decision support system named the [**Tide Gate Optimization Tool**](https://oregontidegates.org/wp-content/uploads/2021/11/Oregons-Tide-Gate-Optimization-Tool-Supporting-Decisions-to-Benefit-Nature-and-People.pdf) to help landowners and other stakeholders balance the potential gain and costs.  The goal of this tool is to identify "the best bang for the buck": given a set of budget levels, which set of barriers will provide the most benefit for each budget? 

## Web Application

The code in this repository is a web interface to the Tide Gate Optimization Tool.  It uses [Panel](https://panel.holoviz.org/) to display a GUI where users can enter optimization parameters -- estuaries they are interested in, a range of costs to consider, and the types of benefits they hope to achieve.   

![](static/start_screenshot.png)

The GUI passes that information to the server, which runs an optimization algorithm.  The output is displayed in the GUI in the form of ROI curves and tables with detailed information about the tide gates included in the optimal solution at various budget levels.

![](static/result_screenshot.png)

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

The first step is to set up the execution environment.

- If you are installing this code on system that will run other Python applications we recommend creating and activating a new virtual environment with `venv`.  You will need Python 3.10 or later.

- If you are setting up a VM dedicated to just this application you can simply install Python 3.10 or later and add the libraries to the global environment.  Log in to your VM with an administrator account.

Obtain a copy of the repo, either by cloning it or downloading the `.zip` file.

Open a terminal and navigate to the directory.  You should see the following structure:

```
tidegates
├── Dockerfile
├── README.md
├── __init__.py
├── bin/
├── requirements.txt
├── static/
├── templates/
└── tidegates/
```

Use PIP to install all the dependencies:

```powershell
> python -m pip install -r requirements.txt
```

Move a copy of the OptiPass command line application to the `bin` directory.  After you do this that directory should have the `exe` file for OptiPass and some Python scripts that are part of the repo:

```
bin
├── OptiPassMain.exe
└── sanitize.py
```

## Running the Server

### Bokeh Server

The simplest way to run the web app is to start Bokeh server, the web framework that is part of the Panel library.   

Start a terminal session.  If you're connecting to a VM you can log in as a regular user; you do not need to run as administrator.

Go to the directory where the app is installed and type the PowerShell command that launches the server:

```powershell
> python .\tidegates\main.py
```

You should see a warning message (explained below) and another message that Python has started a web server listening on port 5006:

```powershell
WARNING:bokeh.server.util:Host wildcard '*' will allow connections originating from multiple (or possibly all) hostnames or IPs. Use non-wildcard values to restrict access explicitly

Launching server at http://localhost:5006
```

Python also opens your default web browser and loads the main page of the web app.

> Note:  the app will not work with Explorer.  Make sure your default browser is Edge, Chrome, or some other modern browser.

### Proxy Server

If you are running the web app on a VM in the cloud the Bokeh server approach should be sufficient and you can ignore that warning message.  

But if you are running it on a Windows host on your own network, the Bokeh developers recommend a more secure setup, where the host runs Nginx, Apache, or some other web server and forwards connections to the tide gates app.  See [Deployment scenarios — Bokeh 3.3.1 Documentation](https://docs.bokeh.org/en/latest/docs/user_guide/server/deploy.html) for more information.

## Connecting to the Server

To connect to the web app using a browser that runs on the same machine as the server (whether that's a VM or a Windows host)  use the URL shown in the startup message:

```
http://localhost:5006
```

(note that is HTTP, and not HTTPS; if your browser displays a warning ignore it and continue).

To connect from a different machine you need to know the IP address of the system running the web app (if you're using Microsoft Remote Desktop the IP address of the remote system is displayed in a corner on the desktop).  Then simply replace `localhost` with the four-part IP address, so the URL has this form:

```
http://xxxx.xxxx.xxxx.xxxx:5006
```

The top level page has two links, one to an`admin` page you can use to monitor the performance of the web app, and one to the `tidegates` app itself.  Click on Tidegates to connect to the web app.

When connecting remotely it's possible to go straight to the web app, bypassing the top level page, if you include `tidegates` in the URL:

```
http://xxxx.xxxx.xxxx.xxxx:5006/tidegates
```

## Using the Tidegates App

## Technical Documentation



