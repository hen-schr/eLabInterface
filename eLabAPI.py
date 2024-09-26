from typing import Union, Literal
import elabapi_python
from elabapi_python.rest import ApiException
from tkinter import filedialog
import os
import json
import markdownify
import pandas as pd
import csv
import numpy as np


class MDInterpreter:
    def __init__(self, raw_content: str):
        self.raw = raw_content
        self.tables = []

    def extract_tables(self, output_format: Literal["dataframes", "list"] = "dataframes", reformat=True):

        commands, tables = self._get_raw_tabular_data()

        data_objects = []

        if output_format == "list":
            for i, table in enumerate(tables):

                converted_table = self._interpret_inline_commands(commands[i], table)

                if converted_table is not None:
                    data_objects.append(converted_table)

        elif output_format == "dataframes":
            for i, table in enumerate(tables):
                converted_table = self._table_array_to_dataframe(table)
                converted_table = converted_table.drop([1])
                converted_table = self._interpret_inline_commands(commands[i], converted_table)

                if reformat:
                    converted_table = self._reformat_dataframe(converted_table)

                data_objects.append(converted_table)

        self.tables = data_objects

        return tables

    def _get_raw_tabular_data(self, separator: str = "|"):

        tables = []
        table_started = False
        start_index = 0
        commands = [[]]

        lines = self.raw.split("\n")

        for i, line in enumerate(lines):
            if len(line) == 0:
                pass
            elif line[0] == ".":
                commands[-1].append(line[1:])
            elif line[0] == separator and not table_started:
                table_started = True
                start_index = i
            elif table_started and line[0] == separator:
                pass
            elif table_started:
                table_started = False
                stop_index = i - 2
                commands.append([])

                tables.append(lines[start_index:stop_index - 2])

        commands = commands[:-1]

        converted_tables = []

        for table in tables:
            conv_table = self._line_list_to_array(table)
            converted_tables.append(conv_table)

        return commands, converted_tables

    @staticmethod
    def _line_list_to_array(table_lines: list[str], separator=" | "):

        converted_table = []

        for line in table_lines:
            converted_table.append(line[2:-2].split(sep=separator))

        return converted_table

    @staticmethod
    def _table_array_to_dataframe(table_array: list[list]):
        df = pd.DataFrame.from_records(table_array)

        return df

    @staticmethod
    def _interpret_inline_commands(commands: list[str], table: Union[list[list], pd.DataFrame]
                                   ) -> Union[list[list], pd.DataFrame]:
        if type(table) is list[list]:
            for command in commands:
                if command == "ignore":
                    table = None
        elif type(table) is pd.DataFrame:
            for command in commands:
                if command == "ignore":
                    table = None
                elif command[:7] == "title\\=":
                    title = command[7:]

        return table

    def _reformat_dataframe(self, dataframe: pd.DataFrame, convert_numbers=True):

        if dataframe.shape[1] == 2:
            header = dataframe[dataframe.columns[0]].values.tolist()
            dataframe = dataframe.set_axis(labels=header, axis=0)
            dataframe = dataframe.drop(dataframe.columns[0], axis="columns")

        else:
            header = dataframe.iloc[0].values.tolist()
            dataframe = dataframe.set_axis(labels=header, axis="columns")
            dataframe = dataframe.drop(0)

            if dataframe.columns[0].lower() in ["probe", "sample", "nr."]:
                header = dataframe[dataframe.columns[0]].values.tolist()
                dataframe = dataframe.set_axis(labels=header, axis=0)
                dataframe = dataframe.drop(dataframe.columns[0], axis="columns")

        dataframe = self._convert_comma_to_point(dataframe, secure=False)

        dataframe = dataframe.convert_dtypes()

        return dataframe

    @staticmethod
    def _convert_comma_to_point(dataframe, secure=True):
        if not secure:
            dataframe = dataframe.apply(lambda x: x.str.replace(',', '.'))
        else:
            pass
        return dataframe

class HelperElabftw:
    """
    As found in the API's documentation (https://github.com/elabftw/elabapi-python)
    """
    def __init__(self, api_key, api_host_url):
        # Configure the api client
        self.configuration = elabapi_python.Configuration()
        self.configuration.api_key['api_key'] = api_key
        self.configuration.api_key_prefix['api_key'] = 'Authorization'
        self.configuration.host = api_host_url
        self.configuration.debug = False
        self.configuration.verify_ssl = True
        # create an instance of the API class
        self.api_client = elabapi_python.ApiClient(self.configuration)
        # fix issue with Authorization header not being properly set by the generated lib
        self.api_client.set_default_header(header_name='Authorization', header_value=api_key)


class ELNResponse:
    def __init__(self, response=None):
        self._response = response
        self._metadata = {
            "id": None,
            "title": None,
            "date": None,
            "elabid": None,
            "created_at": None,
            "modified_at": None,
            "status_title": None,
            "tags": None,
            "fullname": None,
            "experimentType": None
        }
        self._tables = None

    def __str__(self):
        string = "ELNResponse object\n"
        for entry in self._metadata:
            string += f"\t{entry}: {self._metadata[entry]}\n" if self._metadata[entry] is not None else ""

        return string

    def response_to_str(self):
        if self._response is not None:
            string = json.dumps(self._response, indent=4)

            return string
        else:
            return self

    def tables_to_str(self):
        string = ""
        for table in self._tables:
            if type(table) is list:
                for line in table:
                    string += "\t".join(line) + "\n"
            elif type(table) is pd.DataFrame:
                string += table.to_string()

            string += "\n\n"

        return string

    def convert_to_markdown(self) -> Union[str, None]:
        if self._response is None:
            print("No response available to convert to markdown - request data first!")
            return None
        md_body = markdownify.markdownify(self._response["body"])

        return md_body

    def extract_metadata(self):
        self.identify_experiment_type()

        for element in self._metadata:
            if self._metadata[element] is None and element in self._response:
                self._metadata[element] = self._response[element]

    def identify_experiment_type(self):
        experiment_type = "unknown"

        metadata = json.loads(self._response["metadata"])

        if "experimentType" in metadata["extra_fields"]:
            experiment_type = metadata["extra_fields"]["experimentType"]["value"]

        self._metadata["experimentType"] = experiment_type

    def extract_tables(self, output_format: Literal["list", "dataframes"] = "dataframes") -> list[list]:
        md_body = self.convert_to_markdown()

        md_interpreter = MDInterpreter(md_body)

        md_interpreter.extract_tables(output_format=output_format)

        self._tables = md_interpreter.tables

    def process_with_template(self, template=None):
        pass


class ELNImporter:
    def __init__(self, api_key=None, url=None, permissions: Literal["read only", "read and write"] = "read only"):
        self.api_key = api_key
        self.url = url
        self.permissions = permissions
        self.response = None
        self.working = None

    def __str__(self):
        status = "unknown"
        if self.working is not None and self.working:
            status = "working"
        elif self.working is not None and not self.working:
            status = "not working"

        string = f"""
ELNImporter object ({self.permissions})
url: {self.url}
status: {status}
data: {"received" if self.response is not None else "none"}
        """

        return string

    def request(self, query: str = None, limit: int = None, advanced_query: str = None, allow_list: bool = False
                ) -> Union[ELNResponse, list[ELNResponse], None]:
        """
        Sends a request to the API and stores / returns the response as a ELNResponse object
        :param query: Term to search for in the entry titles
        :param limit: Maximum amount of results returned by the response
        :param advanced_query: Element-value pair (i.e. 'id:1234') to filter response
        :param allow_list: If True, a list of ELNResponse objects is returned instead of asking the user to select one
        :return: Response for the given request
        """
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        items = elabapi_python.ItemsApi(api_client)

        if query is not None:
            items_list = items.read_items(_preload_content=False, limit=limit,
                                          q=query)
        elif advanced_query is not None:
            items_list = items.read_items(_preload_content=False, limit=limit,
                                          extended=advanced_query.replace(" ", ""))
        else:
            items_list = items.read_items(_preload_content=False, limit=limit)

        items_list = items_list.json()

        if items_list is None or items_list == []:
            return None
        elif allow_list:
            response_list = []
            for item in items_list:
                response_list.append(ELNResponse(item))
            return response_list

        if len(items_list) == 1:
            selection = items_list[0]
        else:
            selection = select_item_from_api_response(items_list)

        response = ELNResponse(response=selection)

        self.response = response

        return response

    def configure_api(self, api_key=None, url=None, permissions: Literal["read only", "read and write"] = "read only"):
        if api_key is not None:
            self.api_key = api_key
        if url is not None:
            self.url = url

        self.permissions = permissions

        self.ping_api()

    def attach_api_key_from_file(self, file=None):
        if file is None:
            file = filedialog.askopenfilename()

        if os.path.exists(file):

            with open(file, "r") as readfile:
                self.api_key = readfile.read()

    def clear_response(self):
        self.response = None

    def ping_api(self) -> bool:
        """
        Test if the API could be reached with the defined configuration.
        :return: True if communication to API was successful, False if not
        """
        test_response = self.request(limit=1)

        if test_response is not None:
            self.working = True
        else:
            self.working = False

        self.clear_response()

        return self.working


def select_item_from_api_response(response_list):

    print("Received multiple experiments from request:\n")

    for i, item in enumerate(response_list):
        print("\t", i, item["title"])

    selected_response = None

    while True:
        user_selection = input("\nSelect experiment from list: ")
        try:
            selected_index = int(user_selection.replace(" ", ""))
            selected_response = response_list[selected_index]
        except ValueError or IndexError:
            print("Invalid input!")

        if selected_response is not None:
            break

    return selected_response


def list_from_string(string: str, separator="|") -> list:
    """
    Splits the passed string into a list of string values using the separator provided.
    @param string: Any string
    @param separator: Character(s) where lines should be split
    @return: List of the separated string values
    """
    string = string.split(separator)

    lst = []

    for entry in string:
        if entry != "":
            lst.append(try_float_conversion(entry.strip()))

    return lst


def try_float_conversion(string: str, allow_comma=True) -> float or str:
    """
    Attempts to convert the passed string to a float.
    @param string: String to convert to float
    @param allow_comma: If True, string floats using commas instead of points for the decimal separator will be
    converted as well
    @return: Float value of the string or the original string if it could not be converted to float
    """
    try:
        float_value = float(string.replace(",", ".")) if allow_comma else float(string)
        return float_value
    except ValueError:
        return string
