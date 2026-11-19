"""Write everything into one Excel workbook without touching what is already there

Sheets:
    Samples Overview - One row per SRR
    Studies Overview - One row per GSE
    Raw  
"""

import datetime
import os
import shutil
from pathlib import Path
import openpyxl

from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

sameple_overview = []
studies_overview = []

review = []


geo_link = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"
sra_link = "https://www.ncbi.nlm.nih.gov/sra/{}"
pubmed_link = "https://pubmed.ncbi.nlm.nih.gov/{}/"

def open_or_create(path):
    raise NotImplementedError

def gses_already_done(workbook):
    raise NotImplementedError

def add_runs():
    raise NotImplementedError

def add_raw_rows():
    raise NotImplementedError

def update_study():
    raise NotImplementedError

def format_sheets():
    raise NotImplementedError

def fit_columns():
    raise NotImplementedError

def link():
    raise NotImplementedError


def save():
    raise NotImplementedError

