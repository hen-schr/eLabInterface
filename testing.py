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

# plt.plot(np.linspace(0, 100, len(numbers)), numbers)
# plt.show()