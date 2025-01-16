import numpy as np
import pandas as pd
from datetime import datetime

import elab_API
import matplotlib.pyplot as plt

def multiply(x, factor=2):
    y = x ** factor
    return y

from elab_API import ELNImporter

importer = eLabAPI.ELNImporter(debug=True)

# importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")
importer.attach_api_key_from_file("C:/Users/henri/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only", verify_communication=False)

experiment = importer.request(advanced_query="id:5830", limit=1, download_attachments="Downloads/Test")
experiment.toggle_debug()

experiment.save_to_json("Downloads/Test/Demo.json", indent=4)

#experiment.read_response_from_json("C:\\Users\\henri\\Downloads\\2024-11-11-224705-export\\2024-11-11-224705-export\\2024-10-13 - ELN-Demo - affb1138\\export-elabftw.json")

experiment.extract_tables(output_format="dataframes", decimal=",", force_numeric=True)

#data = experiment.tables["some time-resolved measurement data"]

print(experiment.as_dict(duplicate_handling="user selection"))

print(experiment.log_to_str(style="timed"))

#experiment.tables["some time-resolved measurement data"]["mean abs"] = experiment.tables["some time-resolved measurement data"]["absorbance"].mean(axis=1)

#experiment.tables["some time-resolved measurement data"].plot(x="time / h", y="mean abs", kind="scatter")
#data["mean abs"] = data["absorbance"].mean(axis=1)

#data.plot(x="time / h", y=2)

#data = data.apply(lambda i: pd.to_numeric(i, errors="coerce"))

#absorbances = data.iloc[:, 1:4].astype(float, errors="ignore")

#data["mean absorbance"] = data.iloc[:, 1:4].mean(axis=1)
#data["std absorbance"] = data.iloc[:, 1:4].std(axis=1)

#print(data.to_string())
#print(data.columns)

#data.plot(x="time / h", y="mean absorbance", yerr="std absorbance", kind="scatter")
#plt.show()

# plt.plot(np.linspace(0, 100, len(numbers)), numbers)
# plt.show()