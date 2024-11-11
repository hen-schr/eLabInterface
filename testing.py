import numpy as np
import pandas as pd
from datetime import datetime

import eLabAPI
import matplotlib.pyplot as plt

from eLabAPI import ELNImporter

importer = eLabAPI.ELNImporter(debug=True)

# importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")
importer.attach_api_key_from_file("C:/Users/henri/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

experiment = importer.request(advanced_query="id:5693", limit=1, download_attachments="Downloads/Test")
experiment.toggle_debug()

print(experiment.log_to_str(style="timed"))
experiment.save_to_json("Downloads/Test/Demo.json", indent=4)

experiment.read_response_from_json("C:\\Users\\henri\\Downloads\\2024-11-11-224705-export\\2024-11-11-224705-export\\2024-10-13 - ELN-Demo - affb1138\\export-elabftw.json")

experiment.extract_tables(output_format="dataframes", decimal=",")

print(experiment.as_dict("pressure / bar"))
print(experiment.as_dict("device"))

#data = experiment.return_table_as_pd("some time-resolved measurement data")

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