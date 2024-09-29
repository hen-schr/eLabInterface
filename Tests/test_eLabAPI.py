import unittest
import eLabAPI
from unittest.mock import patch
from urllib3 import HTTPResponse


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
        # request returns exactly one item
        with patch("elabapi_python.ItemsApi.read_items") as mocked_api_response:
            mocked_api_response.return_value = self.simple_http_response

            response = self.importer.request()

            self.assertEqual(response._response, {"dummy": "data"})

        # request returns nothing
        with patch("elabapi_python.ItemsApi.read_items") as mocked_api_response:
            mocked_api_response.return_value = HTTPResponse("""[]""".encode("utf-8"))

            response = self.importer.request()

            self.assertIsNone(response)

        # request returns multiple results
        with patch("elabapi_python.ItemsApi.read_items") as mocked_api_response:
            mocked_api_response.return_value = HTTPResponse(
                """[{"dummy": "data"}, {"dummy2": "data2"}]""".encode("utf-8"))

            response = self.importer.request(allow_list=True)

            self.assertEqual(response[0]._response, {"dummy": "data"})
            self.assertEqual(response[1]._response, {"dummy2": "data2"})

    def test_select_item_from_api_response(self):
        with patch("builtins.input") as mocked_selection:
            mocked_selection.return_value = "1"

            value = eLabAPI.select_item_from_api_response([{"title": "0"}, {"title": "1"}, {"title": "2"}])

            self.assertEqual(value, {"title": "1"})

        with patch("builtins.input") as mocked_selection:
            mocked_selection.return_value = "s"

    def test_check_user_selection(self):
        for value, result in [("0", 0), ("1", 1), ("-1", -1), ("d", None), ("A", None),
                              ("abc", None), ("0.123", None), ("7", None)]:
            with self.subTest(value=value):
                self.assertEqual(eLabAPI.check_user_selection(value, ["a", "b", "c"]), result)

    def test_configure_api(self):

        with patch("eLabAPI.ELNImporter.request") as mocked_request:

            mocked_request.return_value = None

            ping = self.importer.ping_api()

            self.assertEqual(ping, False)

            mocked_request.return_value = {"body": "foo"}

            ping = self.importer.ping_api()

            self.assertEqual(ping, True)

    def test_ping_api(self):
        with patch("eLabAPI.ELNImporter.request") as mocked_request:
            mocked_request.response = {"body": "foo"}

            self.importer.ping_api()

            self.assertEqual(self.importer.response, None)


if __name__ == "__main__":
    unittest.main()
