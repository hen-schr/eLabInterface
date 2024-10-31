"""
This small module contains functionalities to access data from the electronic lab notebook (ELN) eLabFTW via the API as
well as methods to convert the data into useful formats for further processing, such as dataframes, lists. Check the
'example_of_use' function at the end of the file for quick reference.

© 2024 by Henrik Schröter, licensed under CC BY-SA 4.0
Email: henrik.schroeter@uni-rostock.de / ORCID 0009-0008-1112-2835
"""
from datetime import datetime
from typing import Union, Literal, Any
import elabapi_python
from tkinter import filedialog
import os
import json
import markdownify
import pandas as pd
import urllib3
import matplotlib.pyplot as plt
from elabapi_python import Upload
from scipy.optimize import direct

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
        self.configuration._debug = False
        self.configuration.verify_ssl = True
        # create an instance of the API class
        self.api_client = elabapi_python.ApiClient(self.configuration)
        # fix issue with Authorization header not being properly set by the generated lib
        self.api_client.set_default_header(header_name='Authorization', header_value=api_key)


class ELNResponse:
    def __init__(self, response: dict=None, response_id: Union[int, str] = None,
                 silent: bool = False, debug: bool = False):
        """
        A general container for a response received from the API
        :param response: The response (in dict format) that was received from the API
        :param response_id: The experiment id, is extracted from the metadata attribute for easier access if not specified upon creation
        :param silent: If True, no messages will be displayed in the console - mainly intended for unittests
        :param debug: If True, all log messages will be printed in the console
        """
        # most basic properties of this class
        self.id = response_id
        self._response = response

        # for logging and debugging
        self.log = ""
        self._silent = silent
        self._debug = debug

        self._log("created ELNResponse instance", "PRC")

        #
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
            "locked_at": None,
            "requestTimeStamp": None
        }

        self._tables = None
        self._attachments = None
        self._download_directory = None

        if response is not None:
            self.extract_metadata()

    def __str__(self):
        string = "ELNResponse object\n"
        for entry in self._metadata:
            string += f"\t{entry}: {self._metadata[entry]}\n" if self._metadata[entry] is not None else ""
        string += f"""\tbody: {len(self._response["body"].encode("utf-8"))} bytes\n"""

        string += f"""\tuploads: {len(self._attachments) if self._attachments is not None else "none"}\n"""

        if self._download_directory is not None:
            string += f"""\tlocal upload directory: {self._download_directory}\n"""

        return string

    def get_attachments(self):
        return self._attachments

    def get_download_directory(self):
        return self._download_directory

    def set_metadata(self, data: dict):
        self._metadata = data
        self._log("original metadata was overwritten by user", "WRN")

    def add_metadata(self, element: str, value: Any):

        if element in self._metadata:
            self._log(f"metadata element '{element}' was overwritten by user", "WRN")

        self._metadata[element] = value

    def get_metadata(self, element: str=None):
        if element is None:
            return self._metadata
        elif element in self._metadata:
            return self._metadata[element]
        else:
            raise AttributeError(f"ELNResponse has no metadata element '{element}'")

    def list_uploads(self):
        if self._attachments is None:
            return None
        string = "Attached uploads:\n"
        for upload in self._attachments:
            string += "\t" + upload.real_name + "\n"

        self._log(string, "USR")

    def toggle_debug(self, state: bool = None):
        if state is None:
            self._debug = not self._debug
        else:
            self._debug = state

    def _log(self, message: str, category: Literal["PRC", "FIL", "ERR", "WRN", "USR"] = None) -> None:
        """
        Logs important events of data processing and other activities
        :param message: Message to add to the log, will be automatically timestamped
        :param category: PRC (processing), FIL (file system related), ERR (error), WRN (warning), USR (user message)
        """
        self.log += f"""\n{datetime.strftime(datetime.now(), "%y-%m-%d %H:%H:%S")}""" \
                    + f"""\t{category if category is not None else "   "}\t{message}"""

        if (not self._silent and category == "USR") or self._debug:
            print(message)

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

    def convert_to_markdown(self, remove_backslashes=True) -> Union[str, None]:
        """
        Converts HTML to Markdown.
        :param remove_backslashes: If True, backslashes that appear as an artifact of the conversion are removed -
        this should be disabled if the original HTML document contains backslashes to begin with
        :return: The converted Markdown text
        """
        if self._response is None:
            self._log("No response available to convert to markdown - request data first!", "USR")
            return None
        md_body = markdownify.markdownify(self._response["body"], heading_style="ATX", strip=["strong", "a", "c"],
                                          newline_style="BACKSLASH")

        # the converter adds backslashes in some edge cases to enable conversion back to html
        # for the purposes of this package, this is not needed and they are removed
        if remove_backslashes:
            md_body = md_body.replace("\\", "")

        return md_body

    def extract_metadata(self):
        self.identify_experiment_type()

        for element in self._metadata:
            if self._metadata[element] is None and element in self._response:
                self._metadata[element] = self._response[element]

        if "id" in self._metadata and self.id is None:
            self.id = self._metadata["id"]
        elif "id" not in self._metadata and self.id is None:
            raise AttributeError("missing essential metadata entry 'id'!")


    def identify_experiment_type(self):
        if self._metadata["experimentType"] is not None:
            return

        experiment_type = "unknown"

        if "metadata" in self._response:
            metadata = json.loads(self._response["metadata"])
        else:
            self._log("could not find metadata in entry, experiment entry might be incomplete", "WRN")
            return


        if "extra_fields" not in metadata:
            self._log("could not find extra fields in metadata, experiment entry might be incomplete",
                      "WRN")
            return

        if "experimentType" in metadata["extra_fields"]:
            experiment_type = metadata["extra_fields"]["experimentType"]["value"]

        self._metadata["experimentType"] = experiment_type

        self._log(f"identified experiment type: {experiment_type}", "PRC")


    def extract_tables(self, output_format: Literal["list", "dataframes"] = "dataframes", reformat=True) -> list[list]:
        md_body = self.convert_to_markdown()

        md_interpreter = MDInterpreter(md_body)

        md_interpreter.extract_tables(output_format=output_format, reformat=reformat)

        self._tables = md_interpreter.tables

        return self._tables

    def save_to_csv(self, file, index=None, separator=";"):

        file = file.replace(".csv", "")

        if index is None:
            for i, table in enumerate(self._tables):
                table.to_csv(f"{file}-{i+1}.csv", encoding="utf-8", sep=separator)
        else:
            self._tables[index].to_csv(file + ".csv", encoding="utf-8", sep=separator)


class ELNImporter:
    def __init__(self, api_key: str = None, url: str = None,
                 permissions: Literal["read only", "read and write"] = "read only",
                 silent: bool = False, debug: bool = False):
        """
        Handles importing ELN entries from eLabFTW by using the python API.
        :param api_key: Key to access the API
        :param url: URL to access the API
        :param permissions: Permissions of the API
        :param silent: If True, no messages will be displayed in the console - mainly intended for unittests
        :param debug: If True, all log messages will also be printed in the console
        """
        self.api_key = api_key
        self.url = url
        self.permissions = permissions
        self.response = None
        self.working = None
        self.log = ""
        self.silent = silent
        self.debug = debug

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

    def _log(self, message: str, category: Literal["COM", "PRC", "FIL", "ERR", "WRN", "USR"]=None) -> None:
        """
        Logs important events of the API communication and data processing
        :param message: Message to add to the log, will be automatically timestamped
        :param category: COM (communication), PRC (processing), FIL (file system related), ERR (error), WRN (warning),
        USR (user message)
        """
        self.log += f"""\n{datetime.strftime(datetime.now(), "%y-%m-%d %H:%H:%S")}""" \
                    + f"""\t{category if category is not None else "   "}\t{message}"""

        if (not self.silent and category == "USR") or self.debug:
            print(message)

    def request(self, query: str = None, limit: int = None, advanced_query: str = None, allow_list: bool = False,
                read_uploads: bool = False, download_uploads = False, return_http_response: bool=False
                ) -> Union[ELNResponse, list[ELNResponse], urllib3.response.HTTPResponse, None]:
        """
        Sends a request to the API and stores / returns the response
        :param query: Term to search for in the entry titles
        :param limit: Maximum amount of results returned by the response
        :param advanced_query: Element-value pair (i.e. 'id:1234') to filter response
        :param allow_list: If True, a list of ELNResponse objects is returned instead of asking the user to select one
        :param read_uploads: If True, all attached files of the ELN entry will be attached to the ELNResponse
        :param download_uploads: If True, all attachments will be downloaded
        :param return_http_response: If True, raw HTTPResponse will be returned instead of an ELNResponse
        :return: Response for the given request
        """
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        items = elabapi_python.ItemsApi(api_client)

        try:
            if query is not None:
                self._log(f"requesting data: q={query}, limit={limit}", "COM")
                raw_items_list = items.read_items(_preload_content=False, limit=limit,
                                              q=query)
            elif advanced_query is not None:
                self._log(f"requesting data: q={advanced_query}, limit={limit}", "COM")
                raw_items_list = items.read_items(_preload_content=False, limit=limit,
                                              extended=advanced_query.replace(" ", ""))
            else:
                self._log(f"requesting data: limit={limit}", "COM")
                raw_items_list = items.read_items(_preload_content=False, limit=limit)

            self._log("received response for request", "COM")

            if return_http_response:
                self.response = raw_items_list

            else:

                self._log("converting HTTPResponse...", "PRC")

                items_list: list[dict] = raw_items_list.json()

                if items_list is None or items_list == []:
                    return None
                elif allow_list:
                    response_list = []
                    for item in items_list:
                        response_list.append(ELNResponse(item))
                    return response_list

                if len(items_list) == 1 and type(items_list) is list:
                    selection = items_list[0]
                else:
                    selection = self.select_item_from_api_response(items_list)

                self.response = ELNResponse(response=selection)
                self._log("successfully created ELNResponse object", "PRC")

                self.response.add_metadata("requestTimeStamp", datetime.strftime(datetime.now(), "%y-%m-%d %H:%M:%S"))


                if read_uploads or download_uploads:
                    self.response.extract_metadata()
                    self.request_uploads(self.response.id)

                if download_uploads:
                    self.download_uploads()

            return self.response

        except urllib3.exceptions.MaxRetryError:
            return None

    def request_uploads(self, identifier) -> list[Upload]:
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        self._log(f"requesting uploads for experiment with id {identifier}", "COM")

        uploadsApi = elabapi_python.UploadsApi(api_client)

        uploads: list[Upload] = uploadsApi.read_uploads("", identifier)

        self.response._attachments = uploads

        self._log(f"received {len(uploads)} uploads", "COM")

        return uploads

    def download_uploads(self, directory="Downloads/") -> None:

        for upload in self.response.get_attachments():
            upload_http = self._get_upload_from_api(upload, format="binary", _preload_content=False)

            with open(directory + upload.real_name, "wb") as writefile:
                writefile.write(upload_http.data)

        download_directory = os.path.abspath(directory)

        self.response._download_directory = download_directory

        self._log(f"wrote {len(self.response.get_attachments())} uploads to directory: {download_directory}", "FIL")

    def _get_upload_from_api(self, upload, **kwargs):
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client
        uploadsApi = elabapi_python.UploadsApi(api_client)
        upload_http: urllib3.response.HTTPResponse = (
            uploadsApi.read_upload("", self.response.id, upload.id, **kwargs))
        return upload_http

    def open_upload(self, selection: Union[str, int]) -> Union[str, any]:

        string_selection = None
        index_selection = None

        if self.response is None:
            self._log("No data was received yet.", "USR")
            return None
        elif self.response.get_attachments() is None:
            self._log("No uploads were attached to the received response.", "USR")
            return None

        if type(selection) is str:
            string_selection = selection
            for attachment in self.response.get_attachments():
                if attachment.real_name == selection:
                    index_selection = self.response.get_attachments().index(attachment)

        elif type(selection) is int:
            index_selection = selection
            string_selection = self.response.get_attachments()[selection]

        object_selection = None

        for upload in self.response.get_attachments():
            if upload.real_name == string_selection:
                object_selection = upload

        directory = self.response.get_download_directory()
        if directory is None:
            pass
        elif directory[-1] != "\\":
            directory += "\\"

        if directory is not None:
            return self._open_file(directory + string_selection)
        elif object_selection is not None:
            data = self._get_upload_from_api(object_selection, _preload_content=False, format="binary")
            with open("Downloads/temp/" + object_selection.real_name, "wb") as writefile:
                writefile.write(data.data)
            self._log(f"""generated temporary file '{"Downloads/temp/" + object_selection.real_name}'""", "FIL")
            re_read_data = self._open_file("Downloads/temp/" + object_selection.real_name)
            os.remove("Downloads/temp/" + object_selection.real_name)
            return re_read_data
        else:
            return None


    @staticmethod
    def _open_file(path) -> Union[str]:
        with open(path, "r") as readfile:
            str_content = readfile.read()
            return str_content

    def select_item_from_api_response(self, response_list):

        self._log("Received multiple experiments from request:", "USR")

        for i, item in enumerate(response_list):
            self._log(f"""\t{i} {item["title"]}""", "USR")

        while True:
            user_selection = input("\nSelect experiment from list: ")

            selected_index = self.check_user_selection(user_selection, response_list)

            if selected_index is not None:
                selected_response = response_list[selected_index]
                break

        return selected_response

    def check_user_selection(self, user_selection, selection_list):
        try:
            selected_index = int(user_selection.replace(" ", ""))
            selection = selection_list[selected_index]
            return selected_index
        except ValueError:
            self._log("Invalid input!", "USR")
            return None
        except IndexError:
            self._log("Invalid input!", "USR")
            return None

    def configure_api(self, api_key=None, url=None, permissions: Literal["read only", "read and write"] = "read only",
                      feedback=True, verify_communication=True):
        if api_key is not None:
            self.api_key = api_key
        if url is not None:
            self.url = url

        self.permissions = permissions

        self._log(f"""set API configuration: url={self.url}, api key={"yes" if self.api_key is not None else "no"}"""
                 + f""", permissions={self.permissions}""", "COM")

        if verify_communication:

            ping = self.ping_api()

            if ping and feedback:
                self._log("API was successfully configured", "COM")
                return True
            elif ping and not feedback:
                return True
            elif not ping and feedback:
                self._log("Could not connect to API using the given configurations", "ERR")
                return False
            else:
                return False
        else:
            return None

    def attach_api_key_from_file(self, file=None):
        if file is None:
            file = filedialog.askopenfilename()

        if os.path.exists(file):

            with open(file, "r") as readfile:
                self.api_key = readfile.read()

            self._log(f"read API key from file: {file}", "FIL")

    def clear_response(self):
        self.response = None

    def ping_api(self) -> bool:
        """
        Test if the API could be reached with the defined configuration.
        :return: True if communication to API was successful, False if not
        """

        self._log("sending test request", "COM")

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

