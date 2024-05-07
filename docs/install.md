# Installation

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

