"""Download run-level metadata for GEO series, R package dante.

For each GSE:
GSExxxxx_complete_metadata.tsv with one row per sequencing run (SRR):
    - The SRA run table (layout, platform, read counts, ...)
    - The GEO sample fields (GSM, title, source, organism, characteristics)
    - A few GEO fields (treatment and growth protocol, description, the series PubMed ID)
    - FASTQ download links from ENA

Used by...
"""

import csv
import io
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GEO_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
RUNINFO_URL = "https://trace.ncbi.nlm.nih.gov/Traces/sra-db-be/runinfo"
EUTILS_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
ENA_URL = "https://www.ebi.ac.uk/ena/portal/api/filereport"

# NCBI allows 3 requests per second without an API key.
PAUSE_SECONDS = 0.4

def read_gse_list():
    raise NotImplementedError

def pull_studies():
    raise NotImplementedError

    

def download_text(url, params, tries=3):
    raise NotImplementedError

def parse_soft():
    raise NotImplementedError

def first():
    raise NotImplementedError

def joined():
    raise NotImplementedError

def column_name():
    raise NotImplementedError

def get_series(gse):
    raise NotImplementedError

def get_samples(gse):
    raise NotImplementedError

def read_runinfo():
    raise NotImplementedError

def get_runs():
    raise NotImplementedError

def get_runs_for(): 
    raise NotImplementedError

def get_fastq_links():
    raise NotImplementedError

def pull_one():
    raise NotImplementedError

