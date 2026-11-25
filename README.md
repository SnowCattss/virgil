# virgil

> **Work in progress.**

Turns GEO/SRA run metadata into one Excel workbook:

## Install (Mac or Linux)

Needs Python 3.8 or newer.

```bash
git clone https://github.com/SnowCattss/virgil.git
cd virgil
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp settings.example.yaml settings.yaml
```

Without installing, `python3 -m virgil ...` works from this folder too. It
offers to install `openpyxl` and `pyyaml` if they are missing.

## Use



## Sheets


## Settings


## Building it


## Tests


## Credit

Fetching follows the approach of [dante](https://github.com/VanBortleLab/dante)
(VanBortle Lab). Data comes from NCBI GEO, NCBI SRA and ENA.
