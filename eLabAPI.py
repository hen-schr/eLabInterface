"""
This small module contains functionalities to access data from the electronic lab notebook (ELN) eLabFTW via the API as
well as methods to convert the data into useful formats for further processing, such as dataframes, lists. Check the
'example_of_use' function at the end of the file for quick reference.

© 2024 by Henrik Schröter, licensed under CC BY-SA 4.0
Email: henrik.schroeter@uni-rostock.de / ORCID 0009-0008-1112-2835
"""

from typing import Union, Literal, Any
import elabapi_python
from tkinter import filedialog
import os
import json
import markdownify
import pandas as pd
import urllib3
import matplotlib.pyplot as plt

module_version = 0.1


class TabularData:
    def __init__(self, data: Union[pd.DataFrame, pd.Series, list, Any] = None, metadata: dict = None, commands=None,
                 title: str = None, datatype: Literal["sample list", "element value", "array"] = None):
        self._data = data
        self._metadata = metadata
        self.title = title
        self.datatype = datatype

        if self.title is None and "title" in self._metadata:
            self.title = self._metadata["title"]
        if self.datatype is None and "datatype" in self._metadata:
            self.datatype = self._metadata["datatype"]

        if commands is not None:
            self.apply_commands(commands)

    def set_data(self, data: Union[pd.DataFrame, pd.Series, list, Any]):
        self._data = data

    def get_data(self):
        return self._data

    def apply_commands(self, commands):
        for command in commands:
            pass

    def plot(self, x: Union[str, int], y: Union[str, int], ax=None, *kwargs):
        if ax is None:
            ax = plt.gca()

    def apply_formula_to_column(self, formula: staticmethod, column, new_column_name):
        pass


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

        # add empty line at the end of lines to make sure that table ends are detected correctly
        lines.append("")

        for i, line in enumerate(lines):
            if len(line) == 0 and not table_started:
                pass

            elif len(line) == 0 and table_started:
                table_started = False
                stop_index = i
                commands.append([])
                tables.append(lines[start_index:stop_index])

            elif line[0] == ".":
                commands[-1].append(line[1:])

            elif line[0] == separator and not table_started:
                table_started = True
                start_index = i

            elif table_started and line[0] == separator:
                pass

            elif table_started:
                table_started = False
                stop_index = i
                commands.append([])

                tables.append(lines[start_index:stop_index])

        commands = commands[:-1]

        converted_tables = []

        for table in tables:
            conv_table = self._line_list_to_array(table)
            converted_tables.append(conv_table)

        return commands, converted_tables

    @staticmethod
    def _line_list_to_array(table_lines: list[str], separator="|"):

        converted_table = []

        for line in table_lines:
            split_line = line[1:-1].split(sep=separator)
            converted_table.append([])
            for entry in split_line:
                converted_table[-1].append(entry.strip())

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
            # TODO secure conversion for the case that entries contain both points and commas
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
    def __init__(self, response=None, response_id=None):
        self.id = response_id
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
            "experimentType": None,
            "userid": None,
            "locked": None,
            "lockedby": None,
            "locked_at": None
        }
        self._tables = None
        self._attachments = None

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
            return ""

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

        if "id" in self._metadata:
            self.id = self._metadata["id"]
        else:
            raise AttributeError("missing essential metadata entry 'id'!")

    def identify_experiment_type(self):
        experiment_type = "unknown"

        metadata = json.loads(self._response["metadata"])

        if "experimentType" in metadata["extra_fields"]:
            experiment_type = metadata["extra_fields"]["experimentType"]["value"]

        self._metadata["experimentType"] = experiment_type

    def extract_tables(self, output_format: Literal["list", "dataframes"] = "dataframes", reformat=True) -> list[list]:
        md_body = self.convert_to_markdown()

        md_interpreter = MDInterpreter(md_body)

        md_interpreter.extract_tables(output_format=output_format, reformat=reformat)

        self._tables = md_interpreter.tables

    def save_to_csv(self, file, index=None, separator=";"):

        if index is None:
            for table in self._tables:
                table.to_csv(file, encoding="utf-8", sep=separator)
        else:
            self._tables[index].to_csv(file, encoding="utf-8", sep=separator)


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

    def request(self, query: str = None, limit: int = None, advanced_query: str = None, allow_list: bool = False,
                read_attachments: bool = False, download_attachments = False) -> Union[ELNResponse, list[ELNResponse], None]:
        """
        Sends a request to the API and stores / returns the response as a ELNResponse object
        :param query: Term to search for in the entry titles
        :param limit: Maximum amount of results returned by the response
        :param advanced_query: Element-value pair (i.e. 'id:1234') to filter response
        :param allow_list: If True, a list of ELNResponse objects is returned instead of asking the user to select one
        :param read_attachments: If True, all attached files of the ELN entry will be attached to the ELNResponse
        :return: Response for the given request
        """
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        items = elabapi_python.ItemsApi(api_client)

        try:
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
                selection = self.select_item_from_api_response(items_list)

            self.response = ELNResponse(response=selection)

            if read_attachments or download_attachments:
                self.response.extract_metadata()
                attachments = self.request_uploads(self.response.id)
                self.response._attachments = attachments
            if download_attachments:
                self.download_uploads()

            return self.response

        except urllib3.exceptions.MaxRetryError:
            return None

    def request_uploads(self, identifier):
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        uploadsApi = elabapi_python.UploadsApi(api_client)

        uploads = uploadsApi.read_uploads("", identifier)

        return uploads

    def download_uploads(self, directory="Downloads/"):

        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        uploadsApi = elabapi_python.UploadsApi(api_client)

        for upload in self.response._attachments:
            upload_http = uploadsApi.read_upload("", self.response.id, upload.id, _preload_content=False, format="binary")

            with open(directory + upload.real_name, "wb") as writefile:
                writefile.write(upload_http.data)

    def select_item_from_api_response(self, response_list):

        print("Received multiple experiments from request:\n")

        for i, item in enumerate(response_list):
            print("\t", i, item["title"])

        while True:
            user_selection = input("\nSelect experiment from list: ")

            selected_index = self.check_user_selection(user_selection, response_list)

            if selected_index is not None:
                selected_response = response_list[selected_index]
                break

        return selected_response

    @staticmethod
    def check_user_selection(user_selection, selection_list):
        try:
            selected_index = int(user_selection.replace(" ", ""))
            selection = selection_list[selected_index]
            return selected_index
        except ValueError:
            print("Invalid input!")
            return None
        except IndexError:
            print("Invalid input!")
            return None

    def configure_api(self, api_key=None, url=None, permissions: Literal["read only", "read and write"] = "read only",
                      feedback=True):
        if api_key is not None:
            self.api_key = api_key
        if url is not None:
            self.url = url

        self.permissions = permissions

        ping = self.ping_api()

        if ping and feedback:
            print("API was successfully configured")
            return True
        elif ping and not feedback:
            return True
        elif not ping and feedback:
            print("Could not connect to API using the given configurations")
            return False
        else:
            return False

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


def list_from_string(string: str, separator="|", strict_conversion=False) -> list:
    """
    Splits the passed string into a list of string values using the separator provided.
    @param string: Any string
    @param separator: Character(s) where lines should be split
    @param strict_conversion: If True, all strings that can not be converted to a number are set to None
    @return: List of the separated string values
    """
    string = string.split(separator)

    lst = []

    for entry in string:
        lst.append(try_float_conversion(entry.strip(), strict=strict_conversion))

    return lst


def try_float_conversion(string: str, allow_comma=True, strict=False) -> float or str:
    """
    Attempts to convert the passed string to a float.
    @param string: String to convert to float
    @param allow_comma: If True, string floats using commas instead of points for the decimal separator will be
    converted as well
    @param strict: If True, strings that could not be converted to a number are converted to None
    @return: Float value of the string or the original string if it could not be converted to float
    """
    if type(string) in [float, int]:
        return string
    elif type(string) is not str:
        raise ValueError

    try:
        float_value = float(string.replace(",", ".")) if allow_comma else float(string)
        return float_value
    except ValueError:
        if strict:
            return None
        else:
            return string


def example_of_use():
    importer = ELNImporter()

    importer.attach_api_key_from_file(
        file="YOUR-API-KEY-FILE")
    importer.configure_api(url="YOUR-API-HOST-URL", permissions="read only")

    importer.ping_api()

    # check state of the importer
    print(importer)

    # request experiment by searching for a term in the experiments' titles
    experiment = importer.request(query="YOUR-QUERY", limit=1)
    print(experiment.response_to_str())

    # request experiment by searching for a term in a specific field
    experiment = importer.request(query="FIELD:YOUR-QUERY", limit=1)
    print(experiment.response_to_str())

    # extract metadata from the api response
    experiment.extract_metadata()

    # extract table data from the experiments body and convert them to dataframes
    experiment.extract_tables(output_format="dataframes")
    print(experiment.tables_to_str())

