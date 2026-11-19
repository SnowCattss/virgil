"""Load settings.yaml and fill in anything it leaves out"""

import sys
from pathlib import Path

import yaml

defaults = {
    "tsv_dir": "geo_metadata",
    "workbook": "combined_metadata.xlsx",
    "assays": ["ATAC-seq"],
    "organisms": ["Homo sapiens"],
    "empty_value": "None",
    "fields": {},
    "open_links_offer": True,
}

def load_settings(path):
    raise NotImplementedError