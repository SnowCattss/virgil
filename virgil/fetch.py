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
pause_seconds = 0.4

def download_text(url, params, tries=3):
    """Download a webpage as text """
    
    full_url = url + "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(full_url, headers= {"User-Agent": "virgil"})

    for attempt in range(1, tries + 1):
        time.sleep(pause_seconds)
        try:
            # with closes the connect at block end
            with urllib.request.urlopen(request, timeout= 30) as response:
                return response.read().decode("utf-8", errors= "replace")
        
        except urllib.error.HTTPError as error:
            if error.code == 429 or error.code >= 500:
                print(f"    server busy ({error.code}), retrying...")
                time.sleep(2 * attempt)
                continue
            
            raise
        
        except urllib.error.URLError as error:
            if isinstance(error.reason, ssl.SSLError):
                sys.exit("\nCertification Error. See ReadMe")
            
            if attempt == tries:
                raise
            print(f"    connection problem ({error.reason}), retrying...")
            time.sleep(2 * attempt)

    raise RuntimeError(f"gave up after {tries} tries: {full_url}")

def read_gse_list(path):
    """Read GSE numbers from a text file
    Accepts one per line, "GSE123456;789101", or "GSE123456, GSE789101"
    Skipps anything not reconized as a GSE number
    """
    found = []
    text = Path(path).read_text(encoding= "utf-8")
    
    #Split on semis, commas, \s, and \n
    for part in re.split(r"[;,\s]+", text):
        part = part.strip().upper()
        
        if not part:
            continue

        if part.isdigit():
            part = "GSE" + part

        if not re.fullmatch(r"GSE\d+", part):
            print(f"Skipping {part!r} in {path}: not GSE number")
            continue

        if part not in found:
            found.append(part)
    return found

def pull_studies(gses, out_dir):
    """Pull every GSE in list into out_dir"""

    out_dir.mkdir(parents= True, exist_ok= True)
    failed = []

    for number, gse in enumerate(gses, start= 1):
        print(f"\n[{number}/{len(gses)}] {gse}")
        
        try:
            pull_one(gse, out_dir)

        except Exception as error:  # noqa: BLE001
            print(f"    FAILED: {error}")
            failed.append(f"{gse}\t{error}")

    print(f"\nDone: {len(gses) -len(failed)} of {len(gses)} studies saved in {out_dir}")

    if failed:
        (out_dir / "failed.txt").write_text("\n".join(failed) + "\n", encoding= "utf-8")
        print("GSE's that failed are in failed.txt")

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

def pull_one(gse, out_dir):
    """Download everything for one GSE adn write it to GSExxxxx_complete_metadata.tsv"""

    series= get_series(gse)
    samples = get_samples(gse)
    print(f"    {len(samples)} samlpes in GEO")

    runs = get_runs(series, samples)
    print(f"    {len(runs)} runs in SRA")

    if not runs:
        raise RuntimeError("No SRA runs found")

    sample_by_srx = {sample["SRX_from_geo"]: sample for sample in samples}
    fastq = get_fastq_links([run["Run"] for run in runs])

    pubmed = ";".join(series.get("Series_pubmed_id", []))
    series_title = first(series, "Series_title")


    rows = []
    for run in runs: 
        row = {"SRR": run["Run"], "SRX": run.get("Experiment", "")}

        for key, value in run.items():
            if key != "Run":
                row[key]= value
        
        row.update(sample_by_srx.get(row["SRX"], {}))
        row["series_title"] = series_title
        row["series_pubmed_id"] = pubmed
        links = fastq.get(row["SRR"], {})

        for field in ("fastq_ftp", "fastq_aspera", "fastq_md5"):
            row[field] = links.get(field, "")
        
        rows.append(row)

    columns = []

    for row in rows:
        
        for key in row:

            if key not in columns:
                columns.append(key)

    out_file = out_dir / f"{gse}_complete_metadata.tsv"
    
    # newline="" lets the csv module control line endings (without Windows gets blank lines).
    with open(out_file, "w", newline= "", encoding= "utf-8") as handle:

        # restval  fills in columns a row dosent have
        writer= csv.DictWriter(handle, fieldnames= columns, delimiter= "\t", restval= "")
        writer.writeheader()
        writer.writerows(rows)
    print(f"     saved {out_file.name}")
    return len(rows)
