# LCICPMS-ui installation

Note: The GUI currently only runs on Python 3.6. Download and install Python 3.6 here: https://www.python.org/downloads/release/python-365/

1)	clone the UI repository: 

a.	Open a Terminal (Mac) or Powershell (Windows) and navigate to the directory where you want to save the gui code 

b.	Clone a branch of the repo by entering the following line in the shell:

git clone --single-branch --branch <name> https://github.com/deweycw/LCICPMS-ui.git

* N.B. Typically you will want to clone the ‘main’ branch (i.e., set <name> to main)


3) create and activate a virtual python3.6 environment:

c.	within the LCICPMS-ui directory, run the following from the command line: 

python3.6 -m venv env

d.	to activate:            
    in MacOS: source env/bin/activate
    in Windows: .\env\Scripts\activate
if you see an error in Windows about the Execution Policy, run the following as an administrator: Set-ExecutionPolicy AllSigned

note: to deactivate the virtual environment, simply run: 	deactivate

2)	install required packages listed in 'requirements-pc.txt' (for PC users) or ‘requirements-mac.txt’ (for Mac users) into virtual env:

a.	open a Terminal (Mac) or Powershell (Windows) and activate virtual env for LCICPMS-ui (if not already activated)

b.	run: pip install -r requirements-mac.txt OR pip install -r requirements-pc.txt

# Starting the GUI

1)	Open a Terminal (Mac) or Powershell (Windows)and navigate to the folder containing the virtual environment and activate the virtual env

2)	Navigate to the folder containing clientRun.py (depending on where you installed your virtual environment, this may be the folder you are already in)

3)	Run the following line within the activated virtual environment: 

python clientRun.py