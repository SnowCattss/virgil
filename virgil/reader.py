"""Read the GSExxxxx_complete_metadata.tsv files in a folder

Used by
"""

import csv
import re
from pathlib import Path

GSE_IN_NAME = re.compile(r"GSE\d+", re.IGNORECASE)

def read_tsv_folder(folder, skip_gses=()):
    raise NotImplementedError

def read_one_file(path):
    raise NotImplementedError