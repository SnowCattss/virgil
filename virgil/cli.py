"""
    virgil build                          Read the .tsv folder, update the workbook
    virgil build --fetch GSE149106        Download first, then build
    virgil build --gse-file list.txt      Download every in list, then build
    virgil fetch GSE149106 optional dst   Only download, no workbook. Assumes run dst unless told otherwise
    virgil fetch --gse-batch list.txt     Download every GSE in list, no workbook 
    virgil --help                         Show options
"""

import argparse
import sys
from pathlib import Path

from .deps import check_dependencies

def main():
    raise NotImplementedError


def gse_list_from(args):
    raise NotImplementedError


def run_fetch():
    raise NotImplementedError


def run_build(args, settings):
    raise NotImplementedError
    

def count_needing_review(book):
    raise NotImplementedError


