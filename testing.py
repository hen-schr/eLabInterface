import numpy as np
import pandas as pd
from datetime import datetime

import eLabAPI
import matplotlib.pyplot as plt

from eLabAPI import ELNImporter

importer = eLabAPI.ELNImporter()

# importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")
importer.attach_api_key_from_file("C:/Users/henri/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

experiment = importer.request(advanced_query="id:5693", limit=1, download_uploads=True)
#experiment.toggle_debug()

experiment.extract_tables(output_format="dataframes", decimal=",")

data = experiment.return_table_as_pd("some time-resolved measurement data")

data = data.apply(lambda i: pd.to_numeric(i, errors="coerce"))

absorbances = data.iloc[:, 1:4].astype(float, errors="ignore")

data["mean absorbance"] = data.iloc[:, 1:4].mean(axis=1)
data["std absorbance"] = data.iloc[:, 1:4].std(axis=1)

print(data.to_string())
print(data.columns)

data.plot(x="time / h", y="mean absorbance", yerr="std absorbance", kind="scatter")
plt.show()

# plt.plot(np.linspace(0, 100, len(numbers)), numbers)
# plt.show()