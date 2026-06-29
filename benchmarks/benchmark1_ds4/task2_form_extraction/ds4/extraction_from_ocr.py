import openpyxl

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Extraction"

headers = ["grid_no", "date", "observer", "canopy_density", "alien_trees_other_species", "alien_plant_other_species_seen"]
ws.append(headers)

rows = [
    # Form 1
    ["Miz.", "illegible", "KI SP Sires", "illegible", "Caffe", "Polygonum"],
    # Form 2
    ["£13", "illegible", "AS PL", "illegible", "illegible", "Polygonum"],
    # Form 3
    ["Ww", "illegible", "illegible", "illegible", "illegible", "illegible"],
    # Form 4
    ["A= oe", "illegible", "illegible", "illegible", "illegible", "illegible"],
    # Form 5
    ["NS", "illegible", "illegible", "illegible", "illegible", "illegible"],
    # Form 6
    ["Mis", "illegible", "illegible", "illegible", "illegible", "Polygonum"],
]

for r in rows:
    ws.append(r)

wb.save("extraction_from_ocr.xlsx")
print("Done.")
