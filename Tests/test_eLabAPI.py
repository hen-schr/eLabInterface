import unittest
import eLabAPI


class TestAPI(unittest.TestCase):

    def reset_objects(self):
        self.importer = eLabAPI.ELNImporter()

    def test_ELNImporter_basic(self):
        importer = eLabAPI.ELNImporter()

        self.assertEqual(importer.working, None)
        self.assertEqual(importer.response, None)
        self.assertEqual(importer.permissions, "read only")

    def test_ELNImporter_configure_api(self):
        importer = eLabAPI.ELNImporter()

        successful_config = importer.configure_api("dummy_key", "dummy_url")
        self.assertEqual(successful_config, False)

        successful_config = importer.configure_api(importer.attach_api_key_from_file("api.key"),
                                                   "https://eln.elaine.uni-rostock.de/api/v2/experiments")
        self.assertEqual(successful_config, True)

    def test_ELNImporter_ping_api(self):
        pass


if __name__ == "__main__":
    unittest.main()
