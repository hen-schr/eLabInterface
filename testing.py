import eLabAPI

importer = eLabAPI.ELNImporter()

importer.attach_api_key_from_file(file="C:/Users/Normaler Benutzer/Documents/__0Henrik/Unikram/Promotion/Datenauswertung/Python/NanoData/eLabAPI/api_key.txt")
importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

importer.ping_api()

experiment = importer.request(query="HS_F020", limit=1)
experiment.extract_metadata()

print(experiment)
