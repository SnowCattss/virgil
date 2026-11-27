"""Write everything into one Excel workbook without touching what is already there

Sheets:
    Samples Overview - One row per SRR
    Studies Overview - One row per GSE
    Raw  
"""

import datetime
import os
import shutil
import warnings
from pathlib import Path

import openpyxl
from openpyxl.formatting.formatting import ConditionalFormattingList
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

studies= "Studies overview"
runs= "Runs overview"
raw= "Raw"

# Column order, change these to change layout
study_columns= ["GSE", "Cell line(s)", "Conditions", "Samples (GSM)", "Runs (SRR)",
                 "Library layout", "What the experiment compares", "Review",
                 "Series title", "PMID", "Left out", "Added on"]

run_columns= ["SRR", "GSE", "Title", "Cell_line", "Treatment", "Time", "Others", "Review"]

# Columns that can turn red
reviewable= {
    studies: study_columns[1:study_columns.index("Review")],
    runs: run_columns[2:run_columns.index("Review")],
}

WRAPPED= {studies:["What the experiment compares"], runs: ["Others"]}

RED = PatternFill("solid", start_color="F4B6B6", end_color="F4B6B6")
HEADER_FILL= PatternFill("solid", fgColor="305496")
HEADER_FONT= Font(bold=True, color="FFFFFF")
LINK_FONT= Font(color="0563C1", underline="single")

GEO_LINK= "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"
SRA_LINK= "https://www.ncbi.nlm.nih.gov/sra/{}"
PUBMED_LINK= "https://pubmed.ncbi.nlm.nih.gov/{}/"

def open_or_create(path):
    path= Path(path)

    if path.exists():
        # Excel and open office add weird formatting rules, virgil adds it's own rules so warning not needed
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            workbook= openpyxl.load_workbook(path)
    

    
    else:
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active) # Removes the empty sheet it spawns with

    for name, columns in ((studies, study_columns), (runs, run_columns), (raw, ["GSE"])):

        if name not in workbook.sheetnames:
            workbook.create_sheet(name).append(columns)
    
    return workbook

def gses_already_done(workbook):
    sheet= workbook[studies]

    return {row[0] for row in sheet.iter_rows(min_row= 2, values_only= True) if row[0]}

def add_runs(workbook, gse, overview_rows, raw_rows):
    """Append new runs to Runs overview and raw. Skips any already there"""
    sheet= workbook[runs]
    existing= {row[0] for row in sheet.iter_rows(min_row= 2, values_only= True) if row [0]}
    added= 0

    for row in overview_rows:

        if row["SRR"] in existing:
            continue

        sheet.append([row[column] for column in run_columns])
        existing.add(row["SRR"])
        added+= 1
    
    add_raw_rows(workbook[raw], gse, raw_rows)
    return added

def add_raw_rows(sheet, gse, raw_rows):
    """append raw runs. Adds a new column if a run has one not seen"""
    header= [cell.value for cell in sheet[1] if cell.value]
    existing= set()

    if "SRR" in header:
        srr_index= header.index("SRR")
        existing= {row[srr_index] for row in sheet.iter_rows(min_row=2, values_only= True)}

    for run in raw_rows:
        if run["SRR"] in existing:
            continue
        run= {"GSE": gse, **run}

        for column in run:
            if column not in header:
                header.append(column)
                sheet.cell(1, len(header), column)
            
        sheet.append([run.get(column, "") for column in header])
        existing.add(run["SRR"]) 


def update_study(workbook, summary):
    """Write/rewrite the studies overview
    summary comes from extract.study_summery. A return only reaches a study that's not in workbook or being redone"""
    sheet= workbook[studies]
    values= [summary.get(column, "") for column in study_columns]
    added_on= study_columns.index("Added on")
    values[added_on]= datetime.date.today().isoformat()

    # Use a row already there or add one
    for number, row in enumerate(sheet.iter_rows(min_row= 2, values_only= True), start= 2):

        if row[0]== summary["GSE"]:
            values[added_on]= row[added_on] or values[added_on] #First date kept

            for column, value in enumerate(values, start= 1):
                sheet.cell(number, column, value)
            
            return
    sheet.append(values)

def format_sheets(workbook):
    """headers, wrapping, links, widths, and red"""
    for sheet in workbook.worksheets:

        for cell in sheet[1]:
            cell.fill= HEADER_FILL
            cell.font= HEADER_FONT
            cell.alignment= Alignment(vertical= "center")
        
        sheet.freeze_panes= "A2"
        fit_columns(sheet)

    for name, columns in WRAPPED.items():
        sheet= workbook[name]
        header= [cell.value for cell in sheet[1]]
        wrapped= {header.index(column) for column in columns}

        for row in sheet.iter_rows(min_row= 2):
            for number, cell in enumerate(row):
                cell.alignment= Alignment(wrap_text= number in wrapped, vertical= "top")

    add_links(workbook)   
    for name in (studies, runs):
        add_review(workbook[name], reviewable[name])

def add_review(sheet, columns):
    """Turn a cell red"""
    header= [cell.value for cell in sheet[1]]
    review_letter= get_column_letter(header.index("Review") + 1)

    #Clears rules first
    sheet.conditional_formatting= ConditionalFormattingList()

    for name in columns:
        letter= get_column_letter(header.index(name) +1)
        formula= f'ISNUMBER(SEARCH("{name}",${review_letter}2))'
        sheet.conditional_formatting.add(f"{letter}2:{letter}1048576",
                                        FormulaRule(formula= [formula], fill= RED))
    
    sheet.auto_filter.ref= sheet.dimensions

def link(cell, url):
    cell.hyperlink= None #dropps and link current there

    if url:
        cell.hyperlink= url
        cell.font= LINK_FONT

def add_links(workbook):
    
    for srr, gse in workbook[runs].iter_rows(min_row= 2, max_col= 2):
        link(srr, SRA_LINK.format(srr.value) if srr.value else None) # added to stop links in empty cells
        link(gse, GEO_LINK.format(gse.value) if gse.value else None)

    STUDIES= workbook[studies]
    pmid_column= study_columns.index("PMID")

    for row in STUDIES.iter_rows(min_row= 2, max_col= pmid_column +1):
        gse, pmid= row[0], row[pmid_column]
        link(gse, GEO_LINK.format(gse.value) if gse.value else None)
        
        #links the first if a study lists more than one
        first_pmid= str(pmid.value).split(";")[0] if pmid.value else ""
        link(pmid, PUBMED_LINK.format(first_pmid) if first_pmid else None)

def fit_columns(sheet, most= 60, check_rows= 500):
    widths= {}

    #mid() stops openpyxl from creating empty rows past end
    for row in sheet.iter_rows(max_row= min(check_rows, sheet.max_row), values_only= True):
        for number, value in enumerate(row, start= 1):
            if value is not None:
                widths[number]= max(widths.get(number, 0), len(str(value)))
    
    for number, width in widths.items():
        sheet.column_dimensions[get_column_letter(number)].width= min(width+2, most)

def save(workbook, path):
    path= Path(path)

    if path.exists():
        backups= path.parent / "backups"
        backups.mkdir(exist_ok= True)
        stamp= datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, backups / f"{path.stem}_{stamp}{path.suffix}")

    temp= path.with_name("~tmp_" + path.name)
    while True:
        try:
            workbook.save(temp)
            os.replace(temp, path)
            return
        except PermissionError:
            answer= input(f"Cant save {path.name}. If open, close and press enter to try again. q to quit:")

            if answer.strip().lower()== "q":
                if temp.exists():
                    temp.unlink()
                raise SystemExit("Aborted and not saved. Original file unchanged.")
    
def remove_study(workbook, gse):
    removed= 0

    for name in (studies, runs, raw):
        sheet= workbook[name]
        header= [cell.value for cell in sheet[1]]

        if "GSE" not in header:
            continue
        
        gse_column= header.index("GSE") +1

        for number in range(sheet.max_row, 1, -1):
            if sheet.cell(number, gse_column).value== gse:
                sheet.delete_rows(number)
                
                if name== runs:
                    removed +=1
    return removed