import numpy as np
import pandas as pd

import eLabAPI
import matplotlib.pyplot as plt

importer = eLabAPI.ELNImporter()

# importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")
importer.attach_api_key_from_file("C:/Users/henri/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

experiment = importer.request(advanced_query="id:5693", limit=1, download_uploads=True)
#experiment.toggle_debug()

experiment.extract_tables(output_format="dataframes")
# experiment.add_metadata("id", 2345)

# print(experiment.convert_to_markdown())
# print(experiment)
# experiment.list_uploads()

# print(experiment.log)

# print(experiment.tables_to_str())

# csv_data = importer.open_upload(2)
csv_data = experiment.open_upload(1)

numbers = csv_data["numberrange"]

plt.plot(np.linspace(0, 100, len(numbers)), numbers)
plt.show()

print(experiment.log_to_str("sections"))