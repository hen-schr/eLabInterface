import eLabAPI

importer = eLabAPI.ELNImporter()

importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
# importer.attach_api_key_from_file("C:/Users/Henrik Schröter/Unibox Rostock/Promotion/Datenauswertung/Python/NanoData/eLabAPI/API_key.txt")

importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

# importer.ping_api()

experiment = importer.request(query="HS_F020", limit=1)
experiment.extract_metadata()
experiment.extract_tables(output_format="dataframes")
experiment.save_to_csv("test.csv", index=2)

print(experiment.tables_to_str())
