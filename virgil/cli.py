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

default_tsv_dir = "GEO Metadata"

def main():
    parser = argparse.ArgumentParser( 
        prog = "virgil",
        description = " Collect GEO/SRA run metadata and build one Excel workbook."
    )

    """Each subcommand gets its own help option "--help" 
    dest = "command" stores what subcommand was used in args.command"""

    commands= parser.add_subparsers( dest = "command", required = True)

    fetch= commands.add_parser("fetch", add_help=False, help= "Download metadata for GEO studies, no workbook")
    fetch.add_argument("-h", "--help", action= "help", help= "Show this help page")
    fetch.add_argument("gse", nargs= "*", help= "GSE numbers, e.g. GSE######")
    fetch.add_argument("--gse-file", help= "Uses text file with GSE numbers, one per line")
    fetch.add_argument("--out", metavar="output_folder", default= default_tsv_dir, help= f"Folder to save the .tsv files in (default: {default_tsv_dir})")

    build= commands.add_parser("build", add_help=False, help= "Read the .tsv folder, update the workbook")
    build.add_argument("-h", "--help", action= "help", help= "Show this help page")
    build.add_argument("--fetch", metavar="GSE#", nargs= "*", help= "Download first, then update workbook.")
    build.add_argument("--gse-file", metavar="Input File", help= "Uses text file with GSE numbers, downloads them, then updates workbook")

    args = parser.parse_args()

    try:
        if args.command == "fetch":
            run_fetch(args)
    except KeyboardInterrupt:
        # User Ctrl+C
        sys.exit("\nAborted.")

def gse_list_from(args):
    """ GSE numbers from cli and/or list file, without repeats"""

    from .fetch import read_gse_list 

    gses = []
    for gse in args.gse:
        gse = gse.strip().upper() 
        if gse not in gses:
            gses.append(gse)

    if args.gse_file:
        for gse in read_gse_list(args.gse_file):
            if gse not in gses:
                gses.append(gse)
    return gses


def run_fetch(args):
    """ Download every study into the --out folder"""

    from .fetch import pull_studies

    if args.gse_file and not Path(args.gse_file).is_file():
        sys.exit(f"File not found: {args.gse_file}")

    gses = gse_list_from(args)
    if not gses:
        sys.exit("Give at least one GSE number, or use --gse-file. See fetch --help")

    print(f"Downloading {len(gses)} studies into {args.out}")
    pull_studies(gses, Path(args.out))

"""
def run_build(args, settings):
    raise NotImplementedError
    

def count_needing_review(book):
    raise NotImplementedError
"""