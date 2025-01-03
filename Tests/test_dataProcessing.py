import unittest
import dataProcessing
import numpy as np
import matplotlib.pyplot as plt
import os
import shutil

class TestDataManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.exists("testfiles/dataProcessing"):
            os.mkdir("testfiles/dataProcessing")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree("testfiles/dataProcessing")

    def setUp(self):
        self.manager = dataProcessing.DataManager(silent=True, working_directory="testfiles/dataProcessing")

    def tearDown(self):
        pass

    def test_basic(self):
        self.assertEqual("testfiles/dataProcessing/", self.manager._working_directory)

        manager = dataProcessing.DataManager()
        cwd = os.getcwd().replace("\\", "/") + "/"
        self.assertEqual(cwd, manager._working_directory)

        manager = dataProcessing.DataManager(working_directory="testfiles\\dataProcessing")
        self.assertEqual("testfiles/dataProcessing/", manager._working_directory)

        self.assertRaises(FileNotFoundError, dataProcessing.DataManager, working_directory="very invalid directory")

    def test_log(self):
        message = "test log message"
        category = "WRN"

        self.manager._log(message, category)

        last_log_message = self.manager.log.split("\n")[-1].split("\t")[-1]
        last_log_cat = self.manager.log.split("\n")[-1].split("\t")[-2]

        self.assertEqual(message, last_log_message)
        self.assertEqual(category, last_log_cat)

    def test_generate_summary(self):

        parameter_list = [
            {"name": "sam", "id": "1234", "job": "scientist"},
            {"name": "ian", "id": 1234},
            {"name": "sam"},
            {"name": True, "id": None},
            {},
            {"job": "scientist", "category": "research"}
        ]

        result_strings = [
            "sam; 1234",
            "ian; 1234",
            "sam",
            "True; None",
            "",
            ""
        ]

        summary_parameters = ["name", "id"]

        for i, param_set in enumerate(parameter_list):
            summary = self.manager.generate_summary(param_set, summary_parameters, handle_missing="ignore")

            self.assertEqual(result_strings[i], summary)

        parameters = {"name": "sam"}
        self.assertRaises(KeyError, self.manager.generate_summary,
                          parameters, summary_parameters, handle_missing="raise")

        summary = self.manager.generate_summary(parameters, summary_parameters, handle_missing="coerce")
        self.assertEqual("sam; None", summary)

    def test_savefig(self):
        xy = np.random.rand(2, 100)

        plt.scatter(*xy)

        self.manager.savefig("testplot.png")

        self.assertTrue(os.path.exists("testfiles/dataProcessing/testplot.png"))

        os.mkdir("testfiles/dataProcessing/subdir")

        self.manager.savefig("testplot.png", "testfiles/dataProcessing/subdir")

        self.assertTrue(os.path.exists("testfiles/dataProcessing/subdir/testplot.png"))

        self.manager.savefig("testplot_2.png", comment="lorem ipsum")
        self.assertEqual("- `testplot_2.png`: lorem ipsum\n", self.manager.file_comments["processed"])

    def test_comment_file(self):
        self.manager.comment_file("testplot.png", "lorem ipsum", "raw")

        self.assertEqual("- `testplot.png`: lorem ipsum\n", self.manager.file_comments["raw"])


    def test_generate_readme(self):
        manager = dataProcessing.DataManager(working_directory="testfiles/dataProcessing", template_file="testfiles/template.md")

        parameters = {"id": 1234, "name": "sam", "job": "scientist"}

        manager.comment_file("testplot.png", "dolor", "processed")
        manager.comment_file("testsheet.csv", "sit amet", "raw")

        manager.generate_readme(parameters)

        with open("testfiles/dataProcessing/README.md", "r") as readfile:
            generated_readme = readfile.read()

        with open("testfiles/filled_template.md", "r") as readfile:
            reference_readme = readfile.read()

        self.assertEqual(reference_readme, generated_readme)

    def test_generate_python_from_jupyter(self):
        self.manager.generate_python_from_jupyter("testfiles/Testbook.ipynb",
                                                  "testfiles/dataProcessing/Testbook.py")

        with open("testfiles/dataProcessing/Testbook.py", "r") as readfile:
            generated_file = readfile.read()

        with open("testfiles/Testbook_converted.py") as readfile:
            reference_file = readfile.read()

        self.assertEqual(reference_file, generated_file)
