# satelliteTracker 
## V 2.000
_________________________________
V 2.000: Added Linkbudget
V 1.100: Bugfix when fetching description
V 1.000: Initial


For use, only satelliteTrackerApp.exe file is needed.

See HSB_SC_SatelliteTrackerApp_Documentation for instructions


# main file structure
# needed when source files are used
# for python intepreter use env/Scripts/python.exe
satelliteTracker/
│
├── app.py                # Main Flask app
├── sc_pyLibrary.py       # Python function library
├── env                   # virtual environment, ontainin all dependancies
└── templates/            # HTML templates
│   └── pageLinkBudget.html
│   └── pageSatelliteTracker.html
└── satic/            # CSS
    └── styles/
        └── styles.css