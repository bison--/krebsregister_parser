from bs4 import BeautifulSoup
import select
import json
import sys
import csv
import os
import re


class dataset:
    def __init__(self):
        self.dataTree = None
        self.wasPiped = False

        if len(sys.argv) > 1:
            if os.path.isfile(sys.argv[1]):
                self.dataTree = BeautifulSoup(open(sys.argv[1]), "html.parser")
            else:
                print('Datei "{}" existiert nicht'.format(sys.argv[1]))
        else:
            try:
                # check if there is a piped file (eg via cat)
                if select.select([sys.stdin, ], [], [], 0.0)[0]:
                    self.wasPiped = True
                    allLines = ''
                    for line in sys.stdin:
                        allLines += line
                    self.dataTree = BeautifulSoup(allLines, "html.parser")

            except Exception as ex:
                # if there is no stdin (windows?)
                pass

        if self.dataTree is None:
            print('enter filename as parameter OR pipe a file')
            sys.exit()

        self.header = dict()
        self.data = dict()
        self.design = list()
        self.year_regex = re.compile("Fallzahlen für das Jahr (?P<year>[0-9]{4}):")

    def processHeader(self, table):
        """Saves metadata and appends the current ID to design list
        """
        metadata = dict()
        for idx, row in enumerate(table.tbody.find_all('tr')):
            cell_id = row.find_all('td')[0].text.strip()
            cell_id = cell_id.strip(":")
            cell_res = row.find_all('td')[1].text.strip()
            cell_res = cell_res.replace("\n", "")
            cell_res = cell_res.replace("\t", " ")
            metadata[cell_id] = cell_res
        self.header[metadata["Lokalisation"]] = metadata
        self.design.append(metadata["Lokalisation"])

    def processData(self, table, id=None):
        if id is None:
            id = len(self.design) - 1
        currentYear = "NA"
        self.data[self.design[id]] = dict()
        for row in table.tbody.find_all("tr"):
            if row.td.has_attr('colspan'):
                try:
                    year = self.year_regex.match(row.text)
                    currentYear = year.group("year")
                except:
                    currentYear = "NA"
                self.data[self.design[id]][currentYear] =  dict()
            else:
                cells = row.find_all("td")
                age = "NA"
                for idx, cell in enumerate(cells):
                    value = cell.text.strip()
                    if idx == 0:
                        age = value.replace("\u00a0","")
                        self.data[self.design[id]][currentYear][age] = list()
                    else:
                        value = value.replace(".","")
                        value = value.replace("-", "0")
                        value = int(value)
                        self.data[self.design[id]][currentYear][age].append(value)
        pass

    def export_json(self, filename):
        with open("{}data.json".format(filename), "w") as f:
            f.write(json.dumps(self.data))
        with open("{}design.json".format(filename), "w") as f:
            f.write(json.dumps(self.design))
        with open("{}meta.json".format(filename), "w") as f:
            f.write(json.dumps(self.header))

        pass

    def export_tab_txt(self, filename):
        """Exports as tab-delimited text file"""

        headers = [
            "Diagnose",
            "Jahr",
            "Altersgruppe",
            "Inzidenz_männlich",
            "Inzidenz_weiblich",
            "Inzidenz_beide",
            "Mortalität_männlich",
            "Mortalität_weiblich",
            "Mortalität_beide"
        ]

        f = open("{}data.txt".format(filename), "w", newline='')
        # write metadata

        a = csv.writer(f, delimiter="\t")
        a.writerow(headers)

        for id, data_by_icd in self.data.items():
            for year, data_by_year in data_by_icd.items():
                for agegroup, valuelist in data_by_year.items():
                    myList = [id, year, agegroup] + valuelist
                    a.writerow(myList)

        f.close()
        pass

    def parse(self):
        for table in self.dataTree.find_all(name="table", attrs={}, recursive=True, text=None, limit=None):
            if table["id"] == "resheader":
                self.processHeader(table)
            elif table["id"] == "datatab":
                self.processData(table)
            else:
                # TODO: stderr is not defined
                print(stderr,"table-tag gefunden, das weder Header noch Daten enthält. Übersprungen.")
        pass


if __name__ == '__main__':
    d = dataset()
    d.parse()
    filename = ''
    if not d.wasPiped:
        filename = input("Ausgabe Filename (auto suffix: data.json, design.json, meta.json, data.txt):")

    if os.path.isfile(filename+"data.json"):
        if d.wasPiped or input("File existiert, überschreiben (N zum abbrechen)?") == "N":
            print("File existiert, abgebrochen")
            sys.exit()

    d.export_json(filename)
    d.export_tab_txt(filename)
