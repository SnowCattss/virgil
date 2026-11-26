"""Checks that the needed packages are installed, and if not, offers to install them."""

import importlib.util
import subprocess
import sys

needed = {"openpyxl": "openpyxl", "pyyaml": "yaml"}

def check_deps(): 
    """Offer to install any missing packages. Exits if they can't be installed"""
    missing = [] 
    for pip_name, import_name in needed.items():
        if importlib.util.find_spec(import_name) is None:
            missing.append(pip_name)
    if not missing:
        return

    # sys.executable is running this script, pip installs into the same place
    command = [sys.executable, "-m", "pip", "install"]
    
    """Outside a virtual environment, install just for this user. Inside one, --user isn't allowed. sys.prefix differs from sys.base_prefix only when a virtual environment is active."""

    if sys.prefix == sys.base_prefix:
        command.append("--user")
    command += missing

    print("virgil needs the following packages to run: " + ", ".join(missing))
    answer = input("Install them now? [y/n]: ").strip().lower()

    if answer != "y":
        sys.exit("Not installed. To install manually, run:\n" + " ".join(command))

    result = subprocess.run(command, check= False)
    if result.returncode != 0:
        sys.exit("pip install failed. If it mentioned an 'externally managed environment' see README")
    
    print("Installed.\n")