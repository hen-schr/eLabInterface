import unittest

import eLabAPI
from unittest.mock import patch
from urllib3 import HTTPResponse
import os


class TestELNImporter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.importer = eLabAPI.ELNImporter()
        self.simple_http_response = HTTPResponse("""[{"dummy": "data"}]""".encode("utf-8"))

    def tearDown(self):
        pass

    def test_basic(self):

        self.assertEqual(self.importer.working, None)
        self.assertEqual(self.importer.response, None)
        self.assertEqual(self.importer.permissions, "read only")

    def test_request(self):

        with patch("elabapi_python.ItemsApi.read_items") as mocked_api_response:

            # request returns exactly one item
            mocked_api_response.return_value = self.simple_http_response

            response = self.importer.request()

            self.assertEqual(response._response, {"dummy": "data"})

            # request returns nothing
            mocked_api_response.return_value = HTTPResponse("""[]""".encode("utf-8"))

            response = self.importer.request()

            self.assertIsNone(response)

            # request returns multiple results
            mocked_api_response.return_value = HTTPResponse(
                """[{"dummy": "data"}, {"dummy2": "data2"}]""".encode("utf-8"))

            response = self.importer.request(allow_list=True)

            self.assertEqual(response[0]._response, {"dummy": "data"})
            self.assertEqual(response[1]._response, {"dummy2": "data2"})

    def test_select_item_from_api_response(self):
        with patch("builtins.input") as mocked_selection:
            mocked_selection.return_value = "1"

            value = self.importer.select_item_from_api_response([{"title": "0"}, {"title": "1"}, {"title": "2"}])

            self.assertEqual(value, {"title": "1"})

    def test_check_user_selection(self):
        for value, result in [("0", 0), ("1", 1), ("-1", -1), ("d", None), ("A", None),
                              ("abc", None), ("0.123", None), ("7", None)]:
            with self.subTest(value=value):
                self.assertEqual(self.importer.check_user_selection(value, ["a", "b", "c"]), result)

    def test_configure_api(self):

        with patch("eLabAPI.ELNImporter.request") as mocked_request:

            mocked_request.return_value = None

            ping = self.importer.ping_api()

            self.assertEqual(ping, False)

            mocked_request.return_value = {"body": "foo"}

            ping = self.importer.ping_api()

            self.assertEqual(ping, True)

    def test_attach_api_key_from_file(self):

        dummy_file = "dummy_key.key"

        with open(dummy_file, "w") as keyfile:
            keyfile.write("dummy key")

        with patch("tkinter.filedialog.askopenfilename") as mocked_filename:
            mocked_filename.return_value = "dummy_key.key"
            self.importer.attach_api_key_from_file()

        self.assertEqual(self.importer.api_key, "dummy key")

        os.remove(dummy_file)

    def test_clear_response(self):
        self.importer.response = eLabAPI.ELNResponse("dummy")

        self.importer.clear_response()

        self.assertIsNone(self.importer.response)

    def test_ping_api(self):
        with patch("eLabAPI.ELNImporter.request") as mocked_request:
            mocked_request.response = {"body": "foo"}

            self.importer.ping_api()

            self.assertEqual(self.importer.response, None)


class TestBasicFunctions(unittest.TestCase):
    def test_list_from_string(self):
        strings = ["a|b|c", "0|1|-2", "a|0|?", "", "1.1|4|a"]
        expected = [["a", "b", "c"], [0, 1, -2], ["a", 0, "?"], [""], [1.1, 4, "a"]]
        
        for s, e in (zip(strings, expected)):
            self.assertEqual(eLabAPI.list_from_string(s), e)

        self.assertEqual(eLabAPI.list_from_string(strings[4], separator=";"), [strings[4]])

    def test_try_float_conversion(self):
        strings = ["1", "-1", "100000000", "1e4", "1.4e-3", "1.4", "a", "", 2, 1.1]
        expected = [1, -1, 100000000, 10000.0, 0.0014, 1.4, "a", "", 2, 1.1]

        invalid_input = eLabAPI.ELNImporter()

        for s, e in (zip(strings, expected)):
            self.assertEqual(eLabAPI.try_float_conversion(s), e)

        with self.assertRaises(ValueError):
            eLabAPI.try_float_conversion(invalid_input)


if __name__ == "__main__":
    unittest.main()
