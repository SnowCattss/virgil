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

from .deps import check_deps

default_tsv_dir = "GEO Metadata"

def main():
    parser = argparse.ArgumentParser( 
        prog = "virgil", add_help=False,
        description = "Collect GEO/SRA run metadata and build one Excel workbook.")
    parser.add_argument("-h", "--help", action="help", help="show this help")

    """Each subcommand gets its own help option "--help" 
    dest = "command" stores what subcommand was used in args.command"""

    commands= parser.add_subparsers( dest = "command", required = True)

    fetch= commands.add_parser("fetch", add_help=False, help= "Download metadata for GEO studies, no workbook")
    fetch.add_argument("-h", "--help", action= "help", help= "Show this help page")
    fetch.add_argument("gse", nargs= "*", help= "GSE numbers, e.g. GSE######")
    fetch.add_argument("--gse-file", help= "Uses text file with GSE numbers, one per line")
    fetch.add_argument("--out", metavar="output_folder", default= None, help= "Folder to save the .tsv files in (default: tsv_dir in settings)")
    fetch.add_argument("--settings", default="settings.yaml", metavar="FILE NAME", help="settings file (default: settings.yaml)")

    build= commands.add_parser("build", add_help=False, help= "Read the .tsv folder, update the workbook")
    build.add_argument("-h", "--help", action= "help", help= "Show this help page")
    build.add_argument("--fetch", default= [], metavar="GSE#", nargs= "*", help= "Download first, then update workbook.")
    build.add_argument("--gse-file", metavar="Input File", help= "Uses text file with GSE numbers, downloads them, then updates workbook")
    build.add_argument("--redo", nargs="+", default= [], metavar= "GSE", help= "Remove given studies from the workbook and add them again (replaces any edits in thier rows)")
    build.add_argument("--tsv-dir", metavar= "FOLDER", help= "folder with the .tsv files (default: tsv_dir in settings)")
    build.add_argument("--workbook", metavar= "FILE NAME", help= "workbook to wrtie (default: workbook in settings)")
    build.add_argument("--settings", default= "settings.yaml", metavar= "FILE NAME", help= "settings file (default: settings.yaml)")
    build.add_argument("-v", "--verbose", action= "store_true", help= "list every run marked NEEDS REVIEW and every run left out")
    build.add_argument("--no-links", action= "store_true", help= "Don't offer to open the GEO pages after fetching")

    args = parser.parse_args()
    
    check_deps()
    from .settings import load_settings
    settings= load_settings(args.settings)

    try:
        if args.command == "fetch":
            run_fetch(args, settings)

        elif args.command == "build":
            run_build(args, settings)

    except KeyboardInterrupt:
        # User Ctrl+C
        sys.exit("\nAborted.")


def gse_list_from(numbers, gse_file):
    """ GSE numbers from cli and/or list file, without repeats"""
    from .fetch import clean_gse, read_gse_list

    if gse_file and not Path(gse_file).is_file():
        sys.exit(f"File not found: {gse_file}")

    gses = []
    for number in numbers:
        gse= clean_gse(number) 
        if not gse:
            sys.exit(f"{number!r} isnt a GSE number")
        if gse not in gses:
            gses.append(gse)

    if gse_file:
        for gse in read_gse_list(gse_file):
            
            if gse not in gses:
                gses.append(gse)
    
    return gses


def run_fetch(args, settings):
    """ Download every study into the --out folder"""
    from .fetch import pull_studies

    gses= gse_list_from(args.gse, args.gse_file)
    if not gses:
        sys.exit("Give at least one GSE number, or --gse-file. See: virgil fetch --help")

    out_dir= Path(args.out or settings["tsv_dir"])
    print(f"Downloading {len(gses)} studies into {out_dir}")
    pull_studies(gses, out_dir)

def run_build(args, settings):
    from . import extract, links, reader, workbook
    from .fetch import pull_studies

    # makes cli argument win over settings
    tsv_dir= Path(args.tsv_dir or settings["tsv_dir"])
    workbook_path= Path(args.workbook or settings["workbook"])

    book= workbook.open_or_create(workbook_path)
    done= workbook.gses_already_done(book)

    redone= False
    
    for gse in gse_list_from(args.redo, None):
        if gse not in done:
            print(f"{gse} isn't in the workbook; it will just be added")
            continue

        if not (tsv_dir / f"{gse}_complete_metadata.tsv").exists() and gse not in gse_list_from(args.fetch, None):
            print(f"Not redoing {gse}: no .tsv found in {tsv_dir}")
            continue
            
        removed= workbook.remove_study(book, gse)
        done.discard(gse)
        redone= True
        print(f"Redoing {gse}: removed its {removed} runs")
    
    if done:
        print(f"{len(done)} studies are already in {workbook_path.name}, skipping them")

    to_fetch= []

    for gse in gse_list_from(args.fetch, args.gse_file):
        already_have_file= (tsv_dir / f"{gse}_complete_metadata.tsv").exists()

        if gse not in done and not already_have_file:
            to_fetch.append(gse)
    
    if to_fetch:
        print(f"Downloading {len(to_fetch)} studies into {tsv_dir}")
        pull_studies(to_fetch, tsv_dir)
    
    if not tsv_dir.is_dir():
        sys.exit(f"Folder not found: {tsv_dir}; set tsv_dir in settings or use --tsv-dir")
    
    studies, problems= reader.read_tsv_folder(tsv_dir, skip_gses= done)

    if not studies and not redone:
        print("No new .tsv files to add. The workbook wasn't changed")

        for problem in problems:
            print("  note: " + problem)
        
        return

    new_gses= []
    total_added= 0

    for number, (gse, runs) in enumerate(sorted(studies.items()), start= 1):
        rows, left_out= extract.build_overview_rows(gse, runs, settings)
        added= workbook.add_runs(book, gse, rows, runs)
        workbook.update_study(book, extract.study_summary(gse, runs, rows, left_out))
        total_added += added
        new_gses.append(gse)

        if not rows:
            problems.append(f"{gse}: no runs matched {settings['assays']} / {settings['organisms']}")
        
        print(f" [{number}/{len(studies)}] {gse}: {added} runs added")

        if args.verbose:
            show_details(rows, left_out)
    
    workbook.format_sheets(book)
    workbook.save(book, workbook_path)
    
    print(f"\nSaved {workbook_path} ({total_added} new runs from {len(new_gses)} studies)")
    review_count= count_needing_review(book)

    if review_count:
        print(f"{review_count} rows on Runs overview need reviewed")

    for problem in problems:
        print(" note: " + problem)

    if settings["offer_to_open_links"] and not args.no_links:
        links.offer_to_open(new_gses)
    
def show_details(rows, left_out):
    """for -v: what was left out and what runs need checked and why"""
    for reason, count in sorted(left_out.items()):
        print(f"    left out: {count} runs ({reason})")
    
    for row in rows:
        if row["Review"]:
            columns= row["Review"].split(": ", 1)[-1]
            print(f"    check {row['SRR']} ({row['Title']}): {columns}")


def count_needing_review(book):
    from .workbook import runs
    
    sheet= book[runs]
    review_column= [cell.value for cell in sheet[1]].index("Review")

    return sum(1 for row in sheet.iter_rows(min_row= 2, values_only= True) if row[review_column])
    
