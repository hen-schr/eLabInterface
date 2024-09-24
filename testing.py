import eLabAPI

importer = eLabAPI.ELNImporter()

importer.attach_api_key_from_file()
importer.configure_api(url="https://eln.elaine.uni-rostock.de/api/v2/experiments", permissions="read only")

importer.ping_api()

print(importer)
