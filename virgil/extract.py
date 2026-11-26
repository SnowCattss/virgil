"""
Rules:
- A value copied straight from a labelled GEO field is trusted.
- A value the tool had to work out (a time read out of free text, "untreated" turned into None, a vague field like source_name) is still written, but its column name goes in Review, which turns the cell red in the workbook.
- empty_value ("None") is only written when the data shows nothing is there. If the tool can't tell, the cell is left blank and marked for review.
"""

import re

#Finds times like "24 h", "24h", "0.5 hr", "30 min", "2 days", "LPS-1h".
time_pattern = re.compile(
    r"(?<![A-Za-z0-9.])(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|min|mins|minutes|d|day|days)(?![A-Za-z])",
    re.IGNORECASE,
)

# The the raw unit -> the short form used in the sheet.
unit_names= {
    "h": "h", "hr": "h", "hrs": "h", "hour": "h", "hours": "h",
    "min": "min", "mins": "min", "minutes": "min",
    "d": "d", "day": "d", "days": "d",
}

def build_overview_rows(gse, runs, settings):
    kept= []
    left_out= {}

    for run in runs:
        reason= why_left_out(run, settings)

        if reason:
            left_out[reason] = left_out.get(reason, 0) + 1
        
        else:
            kept.append(run)

    study_has_treatment= any(first_value(run, settings["fields"]["Treatment"], settings)[0]
                            for run in kept)

    rows= [overview_row(gse, run, study_has_treatment, settings) for run in kept]

    return rows, left_out

def why_left_out(run, settings):
    """Uses the LibraryStrat and organism settings, if left out for other reason returns none"""

    if run.get("LibraryStrategy") not in settings["assays"]:
        return f"assay {run.get('LibraryStrategy') or 'unknown'}"

    if run.get("organism") not in settings["organisms"]:
        return f"organism {run.get('organism') or 'unknown'}"

    return None

def overview_row(gse, run, study_has_treatments, settings):
    """Overview values for one run"""
    review= []

    cell_line, source = first_value(run, settings["fields"]["Cell_line"], settings)

    if not cell_line or source in settings["weak_fields"]:
        review.append("Cell_line")
        
    treatment, check_treatment= pick_treatment(run, study_has_treatments, settings)
    if check_treatment:
        review.append("Treatment")

    time, check_time = pick_time(run, treatment, settings)
    if check_time:
        review.append("Time")

    return{
        "SRR": run["SRR"],
        "GSE": gse,
        "Title": run.get("title", ""),
        "Cell_line": cell_line,
        "Treatment": treatment,
        "Time": time,
        "Others": build_others(run, settings) or settings["empty_value"],
        "Review": ("NEEDS REVIEW: "+ ", ".join(review)) if review else "",
    }

def pick_treatment(run, study_has_treatments, settings):
    empty= settings["empty_value"]
    treatment, _= first_value(run, settings["fields"]["Treatment"], settings)

    if treatment:
    # "NT", "untreated", "control" -> None but should be confirmed.
        if treatment.lower() in settings["untreated_values"]:
            return empty, True
        return treatment, False

    if study_has_treatments:
        return empty, False

    if run.get("treatment_protocol"):
        return "", True
    
    return empty, True

def pick_time(run, treatment, settings):
    empty= settings["empty_value"]

    time, _= first_value(run, settings["fields"]["Time"], settings)
    if time:
        return tidy_time(time) or time, False

    # Untreated runs have no treatment time
    if treatment == empty:
        return empty, False

    # Looks for time inside treatment, then the title
    for text in (treatment, run.get("title", "")):
        found= find_time(text)

        if len(found) == 1:
            return found[0], True
        
        if len(found) > 1:
            # e.g. "1H pulse, 4h chase", won't pick if more than one time
            return "", True

    return "", True


def find_time(text):
    times= []

    for number, unit in time_pattern.findall(text or ""):
        formatted= f"{plain_number(number)}{unit_names[unit.lower()]}"

        if formatted not in times:
            times.append(formatted)
    
    return times

def tidy_time(text):
    match= time_pattern.fullmatch(text.strip())

    if not match:
        return ""
    
    return f"{plain_number(match.group(1))}{unit_names[match.group(2).lower()]}"

def plain_number(text):
    """'0030' -> '30', '0.50' -> '0.5', '24' -> '24'"""

    number= float(text)
    return str(int(number)) if number.is_integer() else str(number)

def build_others(run, settings):
    parts= []

    for column in settings["other_fields"]:
        value= clean(get_field(run, column), settings)

        if value:
            parts.append(f"{column}: {value}")
    
    return "; ".join(parts)

def first_value(run, columns, settings):
    for column in columns:
        value= clean(get_field(run, column), settings)

        if value:
            return value, column
    
    return "", None

def clean(value, settings):
    value = (value or "").strip()
    
    if value.lower() in settings["ignore_values"]:
        return ""
    
    return value

def get_field(run, column):
    if column in run:
        return run[column]
    
    wanted= column.lower()
    for name, value in run.items():
        if name.lower() == wanted:
            return value
    
    return ""
