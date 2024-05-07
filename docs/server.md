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
