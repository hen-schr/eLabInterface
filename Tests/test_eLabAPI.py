import csv
import unittest
import json

import pandas as pd
from elabapi_python import Upload

import eLabAPI
from unittest.mock import patch
from urllib3 import HTTPResponse, BaseHTTPResponse
import os
import urllib3

from eLabAPI import ELNResponse


class TestELNImporter(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists("testfiles/downloads"):
            os.mkdir("testfiles/downloads")

    @classmethod
    def tearDownClass(cls):
        # delete all file created in 'downloads'
        top = "testfiles/downloads"
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
        os.rmdir(top)

    def setUp(self):
        self.importer = eLabAPI.ELNImporter(silent=True)
        self.simple_response = {
            "body": "empty body",
            "id": "00",
            "title": "experiment",
            "metadata":
                """{
                "extra_fields": {"experimentType": {"value": "experiment"}}}"""
        }
        self.simple_http_response = HTTPResponse(("[" + json.dumps(self.simple_response) + "]").encode("utf-8"))

        self.uploads_response = [{"real_name": "test.csv"}, {"real_name": "test2.xml"}]

        self.uploads_response_obj = [Upload(id=1, real_name="test.csv"), Upload(id=2, real_name="test2.xml")]

    def tearDown(self):
        pass

    def test_basic(self):

        self.assertEqual(self.importer.working, None)
        self.assertEqual(self.importer.response, None)
        self.assertEqual(self.importer.permissions, "read only")

    def test_log(self):
        message = "test log message"
        category = "WRN"

        self.importer._log(message, category)

        last_log_message = self.importer.log.split("\n")[-1].split("\t")[-1]
        last_log_cat = self.importer.log.split("\n")[-1].split("\t")[-2]

        self.assertEqual(message, last_log_message)
        self.assertEqual(category, last_log_cat)

    def test_request(self):

        with patch("elabapi_python.ItemsApi.read_items") as mocked_api_response:

            # request returns exactly one item
            mocked_api_response.return_value = self.simple_http_response

            response = self.importer.request()

            self.assertEqual(self.simple_response, response._response)

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

    def test_request_uploads(self):

        # ELNResponse needs to be attached manually to the importer, as no API request was mocked
        self.importer.response = ELNResponse()

        with patch("elabapi_python.UploadsApi.read_uploads") as mocked_api_response:
            mocked_api_response.return_value = self.uploads_response_obj

            uploads = self.importer.request_uploads("arbitrary_identifier")

            self.assertEqual(("", "arbitrary_identifier"), mocked_api_response.call_args.args)

            self.assertEqual(self.uploads_response_obj, uploads)

    def test_download_uploads(self):

        # ELNResponse needs to be attached manually to the importer, as no API request was mocked
        self.importer.response = ELNResponse()
        self.importer.response._attachments = self.uploads_response_obj

        with patch("elabapi_python.UploadsApi.read_upload") as mocked_api_response:
            mocked_api_response.return_value = urllib3.response.HTTPResponse(body=b"0;1\n2;3\n;4;5")

            self.importer.download_uploads("testfiles/downloads/")

        with open("testfiles/downloads/" + self.uploads_response_obj[0].real_name, "r") as readfile:
            file_content = readfile.read()

        self.assertEqual("0;1\n2;3\n;4;5", file_content)
        self.assertTrue(os.path.exists("testfiles/downloads/" + self.uploads_response_obj[0].real_name))
        self.assertTrue(os.path.exists("testfiles/downloads/" + self.uploads_response_obj[1].real_name))

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
        self.importer.response = eLabAPI.ELNResponse(self.simple_http_response.json())

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
            self.assertEqual(eLabAPI.list_from_string(s, strict_conversion=False), e)

        self.assertEqual(eLabAPI.list_from_string(strings[4], separator=";"), [strings[4]])

    def test_try_float_conversion(self):
        strings = ["1", "-1", "100000000", "1e4", "1.4e-3", "1.4", "a", "", 2, 1.1]
        expected = [1, -1, 100000000, 10000.0, 0.0014, 1.4, "a", "", 2, 1.1]

        invalid_input = eLabAPI.ELNImporter()

        for s, e in (zip(strings, expected)):
            self.assertEqual(eLabAPI.try_float_conversion(s), e)

        with self.assertRaises(ValueError):
            eLabAPI.try_float_conversion(invalid_input)


class TestELNResponse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.exists("testfiles/results"):
            os.mkdir("testfiles/results")

    @classmethod
    def tearDownClass(cls):
        # delete all file created in 'results'
        top = "testfiles/results"
        for root, dirs, files in os.walk(top, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
        os.rmdir(top)

    def setUp(self):
        self.response = eLabAPI.ELNResponse(silent=True)
        self.response._response = {
            "body": "empty body",
            "id": "00",
            "title": "experiment",
            "metadata":
                """{
                "extra_fields": {"experimentType": {"value": "experiment"}}}"""}

    def tearDown(self):
        pass

    def test_basic(self):
        for element in self.response._metadata:
            self.assertEqual(self.response._metadata[element], None)

        self.assertEqual(self.response._tables, None)

    def test_response_to_str(self):
        str_response = self.response.response_to_str()

        self.assertIn("""{
    "body": "empty body",
    "id": "00",
    "title": "experiment""", str_response)
        self.response._response = None

        str_response = self.response.response_to_str()

        self.assertEqual(str_response, "")

    def test_tables_to_str(self):
        with open("testfiles/tabletest_2.md", "r") as readfile:
            response = readfile.read()

        with patch("eLabAPI.ELNResponse.convert_to_markdown") as mocked_md_body:
            mocked_md_body.return_value = response

            self.response.extract_tables(reformat=False)

        str_tables = self.response.tables_to_str()

        with open("testfiles/tabletest_2_converted.txt", "r") as readfile:
            reference_str = readfile.read()

        self.assertEqual(str_tables, reference_str)

    def test_convert_to_markdown(self):
        with patch("markdownify.markdownify") as mock_conversion:
            mock_conversion.return_value = "md body"

            md_converted = self.response.convert_to_markdown()

            self.assertEqual(md_converted, "md body")

            self.response._response = None

            md_converted = self.response.convert_to_markdown()

            self.assertEqual(md_converted, None)

            mock_conversion.assert_called_once()

    def test_extract_metadata(self):
        self.response.extract_metadata()

        expected = {"id": "00", "title": "experiment", "experimentType": "experiment"}

        for element in self.response._metadata:
            if element in expected:
                self.assertEqual(self.response._metadata[element], expected[element])
            else:
                self.assertEqual(self.response._metadata[element], None)

    def test_identify_experiment_type(self):
        self.response.identify_experiment_type()

        self.assertEqual(self.response._metadata["experimentType"], "experiment")

    def test_extract_tables(self):

        test_files = ["testfiles/tabletest_1.md", "testfiles/tabletest_2.md"]

        for file in test_files:
            with open(file, "r") as readfile:
                response = readfile.read()

            with patch("eLabAPI.ELNResponse.convert_to_markdown") as mocked_md_body:
                mocked_md_body.return_value = response

                self.response.extract_tables()
                self.assertEqual(type(self.response._tables[0]), pd.DataFrame)

                self.response.extract_tables(output_format="list")
                self.assertEqual(type(self.response._tables[0]), list)

    def test_save_to_csv(self):

        with open("testfiles/tabletest_2.md", "r") as readfile:
            response = readfile.read()

        with patch("eLabAPI.ELNResponse.convert_to_markdown") as mocked_md_body:
            mocked_md_body.return_value = response

            self.response.extract_tables()

        self.response.save_to_csv("testfiles/results/table_conversion.csv", separator=";")

        self.assertTrue(os.path.exists("testfiles/results/table_conversion.csv"))

        csv_content = pd.read_csv("testfiles/results/table_conversion.csv",delimiter=";")
        self.assertEqual(csv_content.shape, (3, 3))


if __name__ == "__main__":
    unittest.main()
