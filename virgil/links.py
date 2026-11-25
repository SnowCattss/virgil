"""Offer to open the GEO page of each new study in the browser"""

import webbrowser

GEO_LINK = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}"

def offer_to_open(gses):
    """ Lists GSO pages for the studies and open them if answered yes"""

    if not gses:
        return
    
    urls= [GEO_LINK.format(gse) for gse in gses]

    print(f"\nGEO Pages for the {len(urls)} new studies:")

    for url in urls:
        print(" " + url)
    
    answer= input(f"Open these {len(urls)} pages in browser? [y/n]: ").strip().lower()
    
    if answer != "y":
        print("GSE cells in workbook will have the links")
        return

    for url in urls:
    
        if not webbrowser.open_new_tab(url):
            print("Could not locate web browser. Use link above or in workbook")
            
            return