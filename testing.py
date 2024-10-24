import pandas as pd

import eLabAPI
import matplotlib.pyplot as plt

importer = eLabAPI.ELNImporter()

importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

# importer.ping_api()

experiment = importer.request(advanced_query="id:5693", limit=1, download_attachments=True)

experiment.extract_metadata()
experiment.extract_tables(output_format="dataframes")

# print(experiment.tables_to_str())
