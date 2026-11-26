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

def parse_soft(text):
    """Split's GEO's soft text into records, one dict per sample """
    records= []
    current= None
    
    for line in text.splitlines():

        if line.startswith("^"):
            current= {"_id": line.split("=", 1)[-1].strip()}
            records.append(current)

        elif line.startswith("!") and current is not None and "=" in line:
            key, value = line[1:].split("=", 1)
            current.setdefault(key.strip(), []).append(value.strip())

    return records

def first(record, field):
    """First value of a field"""

    values= record.get(field, [])
    
    return values[0] if values else ""

def joined(record, field):
    """Join values of a field into one string"""
   
    return " ".join(record.get(field, []))

def column_name(key):
    """Mimic the way dante turn a characteristic lable into colum name"""

    return re.sub(r"[^A-Za-z0-9_.]", ".", key.strip())

def get_series(gse):
    """Series record: title, pubmed ID, links to SRA"""

    text= download_text(GEO_URL, {"acc": gse, "targ": "self", "form": "text", "view": "brief"})
    records= parse_soft(text)

    if not records:
        raise RuntimeError("GEO returned nothing; check GSE number")

    return records[0]

def get_samples(gse):
    """ One ditc per sample in series"""

    text = download_text(GEO_URL, {"acc": gse, "targ": "gsm", "form": "text", "view": "brief"})
    samples= []

    for record in parse_soft(text):
        sample= {
            "GSM": record["_id"],
            "title": first(record, "Sample_title"),
            "source_name": first(record, "Sample_source_name_ch1"),
            "organism": first(record, "Sample_organism_ch1"),
            "library_strategy_geo": first(record, "Sample_library_strategy"),
            "treatment_protocol": joined(record, "Sample_treatment_protocol_ch1"),
            "growth_protocol": joined(record, "Sample_growth_protocol_ch1"),
            "description": joined(record, "Sample_description"),
        }

        for number, line in enumerate(record.get("Sample_characteristics_ch1", []), start= 1):

            if ":" in line:
                key, value= line.split(":", 1)
                sample[column_name(key)] = value.strip()
            
            else:
                sample[f"characteristic_{number}"] = line.strip()

        sample["SRX_from_geo"] = ""

        for relation in record.get("Sample_relation", []):
            match= re.search(r"SRX\d+", relation)

            if match:
                sample["SRX_from_geo"] = match.group(0)
        
        samples.append(sample)
    
    return samples

def read_runinfo(text):
    """The SRA run table comes back as CSV. Return a list of dicts"""
    rows= list(csv.DictReader(io.StringIO(text)))
    
    return [row for row in rows if row.get("Run") and row.get("Run") != "Run"]


def get_runs(series, samples):
    """Each SRR that belongs to this series"""

    wanted_srx= {s["SRX_from_geo"] for s in samples if s["SRX_from_geo"]}

    study_ids = set()
    for relation in series.get("Series_relation", []):
        study_ids.update(re.findall(r"SRP\d+", relation))

    runs= []

    for srp in sorted(study_ids):
        runs.extend(get_runs_for(srp))

     #Keep only runs from this series' samples.
    runs= [r for r in runs if r.get("Experiment") in wanted_srx]

    have = {r.get("Experiment") for r in runs}

    for srx in sorted(wanted_srx - have):
        runs.extend(get_runs_for(srx))

    # Filter again and drop repeats
    unique= {}
    for run in runs:

        if run.get("Experiment") in wanted_srx and run["Run"] not in unique:
            unique[run["Run"]] = run
    
    return list(unique.values())


def get_runs_for(accession): 
    
    try:
        runs = read_runinfo(download_text(RUNINFO_URL, {"acc": accession}))

        if runs:
            return runs
        
    except (urllib.error.URLError, RuntimeError) as error:
        print(f"     Direct SRA lookup field for {accession} ({error}), trying E-utilities")

    found = download_text(EUTILS_URL + "esearch.fcgi",
                          {"db": "sra", "term": accession, "retmax": 10000})
    
    ids= re.findall(r"<Id>(\d+)</Id>", found)

    if not ids:
        return []
    
    text= download_text(EUTILS_URL + "efetch.fcgi",
                        {"db": "sra", "id": ",".join(ids), "rettype": "runinfo", "retmode": "text"})
    
    return read_runinfo(text)

def get_fastq_links(run_ids):
    """{SRR: {fastq_ftp, fastq_aspera, fastq_md5}} from ENA"""
    links = {}

    for srr in run_ids:
        
        try:
            text = download_text(ENA_URL, {
                "accession": srr, "result": "read_run", "format": "tsv", "fields": "run_accession,fastq_ftp,fastq_aspera,fastq_md5"
            })
        except (OSError, RuntimeError) as error:
            print(f"    no ENA links for {srr} ({error})")
            continue

        for row in csv.DictReader(io.StringIO(text), delimiter= "\t"):
            links[row.get("run_accession", srr)] = row

    return links

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