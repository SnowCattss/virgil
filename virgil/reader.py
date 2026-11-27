"""Read the GSExxxxx_complete_metadata.tsv files in a folder"""

import csv
import re
from pathlib import Path

gse_in_name = re.compile(r"GSE\d+", re.IGNORECASE)

def read_tsv_folder(folder, skip_gses=()):
    """ Return ({GSE: [run rows]}, [problem messages])
    Each row is a dict of column name -> text. Studies in skip_gses (in workbook already) are't read"""

    folder= Path(folder)
    
    if not folder.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder}")

    studies= {}
    problems= []
    
    # Sorted so the studies are always read in the same order
    for path in sorted(folder.glob("*.tsv")):
        match= gse_in_name.search(path.name)

        if not match:
            problems.append(f"{path.name}: no GSE number in the file name, skip")
            continue

        gse= match.group(0).upper()

        if gse in skip_gses:
            continue
    
        try:
            rows= read_one_file(path)
        
        except(OSError, UnicodeDecodeError, csv.Error) as error:
            problems.append(f"{path.name}: couldn't read ({error}), skipped")
            continue

        if not rows:
            problems.append(f"{path.name}: no runs in file, skip")
            continue

        #two files for the same GSE: keep each run once, so counts aren't doubled
        have= {run["SRR"] for run in studies.get(gse, [])}
        new_rows= [row for row in rows if row["SRR"] not in have]
        
        if have:
            problems.append(f"{path.name}: another file for {gse}, {len(new_rows)} new runs taken from it")
        studies.setdefault(gse, []).extend(rows)
    
    return studies, problems
    

def read_one_file(path):
    """Read one tsf into a list of dict.s rows without SRR are dropped"""
    
    with open(path, encoding= "utf-8-sig", newline= "") as handle:
        rows= list(csv.DictReader(handle, delimiter= "\t"))

    
    cleaned= []

    for row in rows:
        row= {key: (value or "").strip() for key, value in row.items() if key}

        if row.get("SRR"):
            cleaned.append(row)
    
    return cleaned