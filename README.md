# LCICPMS-ui

 To install:
	
	1) first, clone the main repository: 
	
		git clone --single-branch --branch main https://github.com/deweycw/LCICPMS-ui.git

	
	2) create and activate a virtual python (3.6+) environment:

		a) within the LCICPMS-ui directory, run the following from the command line: python -m venv env

		b) to activate:
			
			in MacOS: source env/bin/activate

			in Windows: .\env\Scripts\activate

				if you see and error in Windows about the Execution Policy, run the following as an administrator: Set-ExecutionPolicy AllSigned

		note: to deactivate the virtual environment, simply run: deactivate

	
	3) install required packages listed in 'requirements.txt' into virtual env:	
		
		a) open a terminal (Mac) or powershell (Windows) and activate virtual env for LCICPMS-ui (if not already activated)
		
		b) run: pip install -r requirements.txt

			You may see the following error: 'subprocess-exited-with-error'. If this appears, you can ignore it. 
