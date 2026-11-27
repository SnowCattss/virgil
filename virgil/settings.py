"""Load settings.yaml and fill in anything it leaves out"""

import copy
import sys
from pathlib import Path

import yaml

defaults = {
    "tsv_dir": "GEO Metadata",
    "workbook": "curated_metadata.xlsx",
    "assays": ["ATAC-seq"],
    "organisms": ["Homo sapiens"],
    "empty_value": "None",
    "fields": {
        "Cell_line": ["cell.line", "cell_line", "cell.type", "tissue", "source_name"],
        "Treatment": ["treatment", "treatment.condition", "agent"],
        "Time": ["time", "timepoint", "time.point"],
    },
    "weak_fields": ["tissue", "source_name"],
    "other_fields": ["genotype", "sgrna", "stimulation", "transfection"],
    "varying_fields": ["growth_protocol"],
    "ignore_values": ["n/a", "na", "--", "-", "hg19", "hg38"],
    "untreated_values": ["nt", "untreated", "control", "none", "no treatment", "mock"],
    "offer_to_open_links": True,
}

def load_settings(path):
    """Read the YAML file and return a dict with each setting""" 

    settings= copy.deepcopy(defaults)

    path= Path(path)

    if not path.exists():
        print(f"No {path.name} found, using the default settings")
        return settings

    try:
        user= yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    
    except yaml.YAMLError as error:
        sys.exit(f"{path.name} has an error :\n{error}")

    if not isinstance(user, dict):
        sys.exit(f"{path.name} should be a list of 'name: value' linse")

    for key, value in user.items():
        
        if key not in defaults:
            print(f"Ignoring unknown setting '{key}' in {path.name} (typo?)")
            continue

        if isinstance(defaults[key], list) and isinstance(value, str):
            value= [value]
        
        if key== "fields" and isinstance(value, dict):
            settings["fields"].update(value)
        
        else:
            settings[key]= value
    

    if settings["empty_value"] is None:
        settings["empty_value"]= "None"

    # Lowercase now for later comparisons
    for key in ("ignore_values", "untreated_values"):
        settings[key]= [str(value).lower() for value in settings[key]]
    return settings