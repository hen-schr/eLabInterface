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
import yaml
from elabapi_python import Upload
from io import StringIO
import tkinter as tk

module_version = 0.1


class ELNDataLogger:
    """
    Contains most essential functionalities for ELN entry processing to facilitate debugging and general transparency.
    """
    def __init__(self, debug=False, silent=False):
        """
        :param silent: If True, no messages will be displayed in the console - mainly intended for unittests
        :param debug: If True, all log messages will be printed in the console
        """

        self.log = ""
        self._debug = debug
        self._silent = silent

        self._log(f"created instance of {self.__class__.__name__}", "PRC")

    def input(self, message,
              input_type: Literal["int", "float", "str"] = None,
              value_range: tuple[Union[float, str], Union[float, str]] = None) -> Union[str, int, float]:
        """
        Assures that the user input was supplied in the correct type and directly converts it.
        :param message: message to display in the console, see builtins.input
        :param input_type: value type the input is converted to
        :param value_range: maximum and minimum allowed value for the input (for float and int)
        :return: User input in the desired format
        """

        type_dict = {"int": int, "float": float, "str": str}

        input_type = type_dict[input_type]

        while True:
            user_input = input(message)
            if input_type is None:
                self._log(f"User input: {user_input}", "PRC")
                return user_input
            else:
                try:
                    user_input = input_type(user_input)

                    if value_range is not None:
                        if value_range[0] <= user_input <= value_range[1]:
                            self._log(f"User input: {user_input}", "PRC")
                            return user_input
                        else:
                            print(f"invalid input: enter a value between {value_range[0]} and {value_range[1]}")
                    else:
                        self._log(f"User input: {user_input}", "PRC")
                        return user_input

                except ValueError:
                    print(f"invalid input: type {input_type.__name__} required")

    def _log(self, message: str, category: Literal["PRC", "FIL", "ERR", "WRN", "USR", "COM"] = None) -> None:
        """
        Logs important events of data processing and other activities
        :param message: Message to add to the log, will be automatically timestamped
        :param category: PRC (processing), FIL (file system related), ERR (error), WRN (warning), USR (user message),
        COM (communication)
        """
        self.log += f"""\n{datetime.strftime(datetime.now(), "%y-%m-%d %H:%H:%S.%f")}""" \
                    + f"""\t{category if category is not None else "   "}\t{message}"""

        if (not self._silent and category == "USR") or self._debug:
            print(message)

    def toggle_debug(self, state: bool = None):

        if state is None:
            self._debug = not self._debug

        else:
            self._debug = state


class TabularData(ELNDataLogger):
    def __init__(self, data: Union[pd.DataFrame, pd.Series, list, dict, Any] = None, metadata: dict = None,
                title: str = None, datatype: Literal["sample list", "element value", "array"] = None, debug=False, silent=False):

        super().__init__(silent=silent, debug=debug)
        self._data = data
        self._metadata = metadata
        self.title = title
        self.datatype = datatype

        if self._metadata is not None:
            if self.title is None and "title" in self._metadata:
                self.title = self._metadata["title"]
            if self.datatype is None and "datatype" in self._metadata:
                self.datatype = self._metadata["datatype"]

    def __setitem__(self, key, value):
        if type(self._data) is pd.DataFrame:
            self._data[key] = value
            self._log(f"created new column '{key}'", "PRC")
        elif type(self._data) is dict:
            self._data[key] = value
            self._log(f"created new entry '{key}'", "PRC")
        else:
            raise AttributeError(f"Values can not be set for data of type {type(self._data)}")

    def __getitem__(self, item: Union[str, int]):
        if type(self._data) is pd.DataFrame:
            if type(item) is str:
                return self._data[item]
            else:
                return self._data.iloc[:, item]
        elif type(self._data) is dict:
            return self._data[item]
        else:
            raise AttributeError(f"Values can not be retrieved for data of type {type(self._data)}")

    @property
    def width(self):
        if self._data is not None:
            return self._data.shape[1]
        else:
            return None

    @property
    def height(self):
        if self._data is not None:
            return self._data.shape[0]
        else:
            return None

    def to_string(self) -> str:
        if type(self._data) is pd.DataFrame:
            return self._data.to_string()

    def convert_to_list(self):
        self._data = self.to_list()

    def to_list(self) -> list:
        if type(self._data) is pd.DataFrame:
            list_data = []
            for i in range(len(self._data.columns)):
                list_data.append(self._data.iloc[:, i].tolist())
            return list_data

    def set_data(self, data: Union[pd.DataFrame, pd.Series, list, Any]):
        self._data = data

    def set_headers(self, headers):
        self._data.columns = headers

    def data(self):
        return self._data

    def convert_to_numeric(self, force=False, null_value=None):

        converted = None

        if type(self._data) is pd.DataFrame:
            converted = self._convert_pd_to_numeric(force=force)
        elif type(self._data) is list:
            converted = self._convert_list_to_numeric(force=force, null_value=null_value)

        if converted is not None:
            self._data = converted
            return True
        else:
            return False

    def _convert_pd_to_numeric(self, force=False) -> pd.DataFrame:

        numeric_table = pd.DataFrame()

        for i, column in enumerate(self._data.columns.values):
            try:
                numeric_table.insert(i, column, self._data.iloc[:, i].apply(pd.to_numeric, errors="raise"),
                                     True)
            except ValueError:
                if force:
                    numeric_table.insert(i, column,
                                         self._data.iloc[:, i].apply(pd.to_numeric, errors="coerce"),
                                         True)
                else:
                    numeric_table.insert(i, column, self._data.iloc[:, i], True)

        return numeric_table

    def _convert_list_to_numeric(self, data=None, force=False, null_value=None) -> list:

        converted_list = []

        if data is None:
            data = self._data

        for item in data:
            if type(item) is list:
                converted_list.append(self._convert_list_to_numeric(data=item, force=force, null_value=null_value))
            else:
                try:
                    converted_list.append(float(item))
                except ValueError:
                    if force:
                        converted_list.append(null_value)
                    else:
                        converted_list.append(item)

        return converted_list

    def plot(self, x: Union[str, int], y: Union[str, int], ax=None, **kwargs):
        if ax is None:
            ax = plt.gca()
        if type(self._data) is pd.DataFrame:
            self._data.plot(x=x, y=y, ax=ax, **kwargs)
        elif type(self._data) is list:
            buffer = pd.DataFrame({1: self._data[x], 2: self._data[y]})
            buffer.plot(x=1, y=2, ax=ax, **kwargs)

    def apply_formula_to_column(self, formula: staticmethod, column: Union[int, str], new_column_name: str, **kwargs):
        if type(self._data) is pd.DataFrame:
            arguments = ", ".join(f"{key}={value}" for key, value in kwargs.items())
            if type(column) is str:
                self._log(f"applying '{formula.__name__}' to column '{column}' with arguments '{arguments}' -> '{new_column_name}'", "PRC")
                self[new_column_name] = self._data[column].apply(formula, **kwargs)
            elif type(column) is int:
                self._log(f"applying function '{formula.__name__}' to column '{self._data.columns.values[column]}' with arguments '{arguments}' -> '{new_column_name}'", "PRC")
                self[new_column_name] = self._data.iloc[:, column].apply(formula, **kwargs)
            else:
                raise ValueError
        else:
            self._log("this function is not available for this type of data at the moment", "USR")


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


class FileManager(ELNDataLogger):
    """
    Contains all functionality related to reading from and writing to local files.
    """
    def __init__(self, silent=False, debug=False):

        super().__init__(debug, silent)

    def open_file(self, path, open_as: Literal["txt", "csv", "json"] = None, **kwargs
                  ) -> Union[pd.DataFrame, str, None]:

        if not os.path.exists(path):
            raise FileNotFoundError(f"Invalid path: '{path}'!")

        if open_as is not None:
            filetype = open_as
        else:
            filetype = self.analyze_filetype(path)

        if filetype == "csv":
            return self.open_csv(path, **kwargs)
        if filetype == "json":
            return self.open_json(path, **kwargs)
        elif filetype == "txt":
            with open(path, "r") as readfile:
                str_content = readfile.read()
            return str_content
        else:
            raise NotImplementedError(f"Filetype '{filetype}' is not supported yet!")

    @staticmethod
    def write_data_to_file(data, file_path, mode="w"):
        with open(file_path, mode) as writefile:
            writefile.write(data)

    @staticmethod
    def analyze_filetype(path):
        return path[path.rfind(".") + 1:]

    @staticmethod
    def write_to_csv(path: str, data: Union[pd.DataFrame, TabularData], **kwargs) -> None:
        """
        Writes a pandas dataframe to csv.
        :param path: full path to the file to write the csv data to
        :param data: pandas.DataFrame or elab_API.TabularData object
        """

        path = path.replace(".csv", "")

        if "encoding" not in kwargs:
            kwargs["encoding"] = "utf-8"


        if type(data) is pd.DataFrame:
            data.to_csv(f"{path}.csv", **kwargs)
        elif type(data) is TabularData:
            data.data().to_csv(f"{path}.csv", **kwargs)

    # noinspection PyTypeChecker
    def open_csv(self, path, check=True, remove_metadata=True, metadata_delimiter="---\n", read_metadata=False, **kwargs):

        metadata = {}

        if remove_metadata or read_metadata:
            raw_content = self.open_file(path, open_as="txt")
            raw_content = raw_content.split(metadata_delimiter)
            if len(raw_content) == 1:
                csv_data = pd.read_csv(StringIO(raw_content[0]), **kwargs)
            elif len(raw_content) == 3:
                csv_data = pd.read_csv(StringIO(raw_content[2]), **kwargs)
            else:
                csv_data = pd.read_csv(path, **kwargs)

            if read_metadata:

                metadata_format = kwargs.get("metadata format", "yaml")

                metadata = self.read_metadata_string(raw_content[1], metadata_format=metadata_format)

        else:
            csv_data = pd.read_csv(path, **kwargs)

        if check:
            if csv_data.shape[1] == 1:
                self._log("CSV file seems to have only one column:", "USR")
                self._log(f"Example row: {csv_data[:1]}", "USR")
                self._log(f"Set delimiter and try again or type 'c' to continue", "USR")
                delimiter = input(">> ")
                if delimiter.strip() == "q":
                    return csv_data
                else:
                    csv_data = self.open_csv(path, check=True, delimiter=delimiter)

        if read_metadata:
            return csv_data, metadata
        else:
            return csv_data

    @staticmethod
    def read_metadata_string(data_string, metadata_format: Literal["yaml", "json"] = "json") -> dict:

        metadata = {}

        if metadata_format == "yaml":
            metadata = yaml.safe_load(data_string)
        elif metadata_format == "json":
            metadata = json.loads(data_string)

        return metadata

    @staticmethod
    def open_json(path, **kwargs):

        data = json.load(path, **kwargs)

        return data

    @staticmethod
    def get_absolute_path(path):
        return os.path.abspath(path)

    @staticmethod
    def unify_directory(path: str) -> str:
        """
        Converts a given path string into a unified format to ensure consistency.
        :param path: Absolute or relative path to the directory
        :return: Path string in the format 'path/to/directory/'
        """
        path = path.replace("\\", "/")

        if path[-1] != "/":
            path += "/"
        if path[0] == "/":
            path = path[1:]

        return path


class ELNResponse(ELNDataLogger):
    """
    A general container for a response received from the API with some processing functions.
    """
    def __init__(self, response: dict = None, response_id: Union[int, str] = None, silent: bool = False,
                 debug: bool = False):
        """
        :param response:        The response (in dict format) that was received from the API
        :param response_id:     The experiment id, is extracted from the metadata attribute for easier access if not \
                                specified upon creation
        """

        super().__init__(debug, silent)

        # most basic properties of this class
        self.id = response_id
        self._response = response

        # for logging and debugging
        self._importer_log = None

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
            "requestTimeStamp": None,
            "orcid": None
        }

        self._tables = None
        self._attachments = None
        self._download_directory = None
        self.__file_manager = FileManager(silent=silent, debug=debug)

        if response is not None:
            self.extract_metadata()

    def __str__(self) -> str:
        """
        Summarizes the most important data of the response object.
        """
        string = "ELNResponse object\n"

        for entry in self._metadata:
            string += f"\t{entry}: {self._metadata[entry]}\n" if self._metadata[entry] is not None else ""

        string += f"""\tbody: {len(self._response["body"].encode("utf-8"))} bytes\n"""

        string += f"""\tuploads: {len(self._attachments) if self._attachments is not None else "none"}\n"""

        if self._download_directory is not None:
            string += f"""\tlocal upload directory: {self._download_directory}\n"""

        return string

    def __getitem__(self, item):
        """
        Access data inside the ELN response (metadata, tabular data) in a dict-like way.

        Warning: You might run into problems when duplicate entries are present inside the entry's tables. Use
        self.as_dict() to specify the behavior in such cases.
        """
        eln_dict = self._metadata
        if self._tables is not None:
            eln_dict.update(self._get_dict_from_tables(duplicate_handling="raise error"))

        return eln_dict[item]

    def log_to_str(self, style: Literal["plain", "timed", "sections"] = "timed",
                   filter_categories: list[Literal["USR", "COM", "PRC, FIL"]] = None) -> str:
        """
        Returns the log entries of the Response instance, as well as the attached Importer and FileManager if desired.

        :param style:   Format of the log string. 'plain' - only the response log is returned. 'timed' - all three logs
                        are merged and sorted by time.'sections' - the three logs are displayed in separate sections
        :param filter_categories: Select one or more log categories to be displayed instead of showing everything
        :return:        The formatted log string
        """
        if style == "plain":
            return self.log

        elif style == "timed":
            log = self._dissect_log(self.log, "Response")
            import_log = self._dissect_log(self._importer_log, "Importer") if self._importer_log is not None else []
            file_log = self._dissect_log(self.__file_manager.log, "Filemanager")

            sorted_log_entries = sorted(log + import_log + file_log, key=lambda time: time[0])

            log_string = ""

            for entry in sorted_log_entries:
                if filter_categories is None or entry[1].split("\t")[1] in filter_categories:
                    log_string += entry[0].strftime("%y-%m-%d %H:%H:%S.%f") + "\t" + entry[1] + "\n"

            return log_string

        elif style == "sections":

            null_message = "\nNothing here"

            log = self.log
            import_log = self._importer_log if self._importer_log is not None else null_message
            file_log = self.__file_manager.log if self.__file_manager is not None else null_message

            log_string = f"""
=== Response ===
{log}
            
=== Importer ===
{import_log}
            
=== FileManager ===
{file_log}
            """

            return log_string

    @staticmethod
    def _dissect_log(log: str, specification=None) -> list[tuple[datetime.time, str]]:
        """

        Separates a log string into a list of time-resolved log entries.

        :param log: The log string to process
        :param specification: Is prepended to the log message to specify its origin or category
        :return: A list of date-message-tuples
        """
        specification = f"{specification}\t" if specification is not None else ""

        log_lines = []
        for line in log.strip("\n ").split("\n"):
            try:
                split_line = line.split("\t", 1)
                date = datetime.strptime(split_line[0], "%y-%m-%d %H:%M:%S.%f")
                content = f"{specification}" + split_line[1]
                log_lines.append((date, content))
            except ValueError:
                pass

        return log_lines

    def get_summary_string(self, parameters: list[str] = None, handle_missing: Literal["raise", "ignore"] = "raise") -> str:
        """
        Generates a string containing the requested information.

        Can be used to quickly display information about the dataset or attach this information to files or plots.
        :param parameters: List of keys to retrieve information from the ELNResponse
        :param handle_missing: Behavior in case of missing parameters. 'raise' raises a ValueError; 'ignore' sets the missing value to None
        :return: String of parameters, with units in case of numeric values
        """

        if parameters is None:
            parameters = self.as_dict().keys()

        summary_parameters = {}

        for param in parameters:
            try:
                summary_parameters[param] = self[param]
            except KeyError:
                if handle_missing == "raise":
                    raise KeyError(f"Missing required parameter '{param}'")
                elif handle_missing == "ignore":
                    self._log(f"missing required parameter '{param}'", "WRN")

        info_display = ""

        for param in summary_parameters:
            info_display += summary_parameters[param]
            info_display += (" " + param.split(" / ")[-1].strip()) if (
                    is_float(summary_parameters[param]) and "/" in param) else ""
            info_display += "; "

        info_display = info_display[:-2]

        return info_display

    """
    Getters and setters
    """
    def get_attachments(self):
        return self._attachments

    def get_download_directory(self):
        return self.__file_manager.unify_directory(self._download_directory)

    def set_download_directory(self, path):
        self._download_directory = self.__file_manager.unify_directory(path)
        self._log(f"set download directory to {self._download_directory}")

    def set_metadata(self, data: dict):
        self._metadata = data
        self._log("original metadata was overwritten by user", "WRN")

    def add_metadata(self, element: str, value: Any):

        if element in self._metadata and self._metadata[element] is not None:
            self._log(f"metadata element '{element}' was overwritten by user", "WRN")

        self._metadata[element] = value

    def get_metadata(self, element: str=None):
        if element is None:
            return self._metadata
        elif element in self._metadata:
            return self._metadata[element]
        else:
            raise AttributeError(f"ELNResponse has no metadata element '{element}'")

    def clear(self, selector: Literal["all", "tables", "attachments", "metadata"] = "all") -> None:
        """
        Deletes some data of the ELN response.
        :param selector:
        :return: None
        """
        if selector == "all":
            self._tables = None
            self._attachments = None
            self._download_directory = None
        elif selector == "tables":
            self._tables = None
        elif selector == "attachments":
            self._attachments = None
            self._download_directory = None
        elif selector == "metadata":
            self.set_metadata({})

        self._log(f"cleared {selector} of response", "PRC")

    def add_importer_log(self, importer_log):
        self._importer_log = importer_log

    def list_attachments(self, selector=None):
        """
        Prints a list of files attached to the experiment.
        """
        if self._attachments is None:
            return None
        string = "Attached uploads:\n"
        for upload in self._attachments:
            if selector is None:
                string += "\t" + upload.real_name + "\n"
            if selector is not None and upload.real_name[-len(selector):] == selector:
                string += "\t" + upload.real_name + "\n"

        self._log(string, "USR")

    def toggle_debug(self, state: bool = None):

        if state is None:
            self._debug = not self._debug

        else:
            self._debug = state

    def response_to_str(self, indent: str = 4, **kwargs) -> str:
        """
        Converts the response into a formatted json string.
        :param indent: The indentation to use when formatting the json string
        :return: The converted response data in string format
        """
        if self._response is not None:
            string = json.dumps(self._response, indent=indent, **kwargs)

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
            elif type(table) is TabularData:
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

        if "metadata" in self._response and self._response["metadata"] is not None:
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

    def open_attachment(self, selection: Union[str, int], open_as: str = None, **kwargs) -> Union[str, any, None]:
        """
        Returns the content of an upload associated with the ELN entry.

        Attachments need to be downloaded and located in the specified download directory for this to work.
        Use self.list_attachments to get a list of all available attachments.
        :param selection: The name of the upload file (i.e. 'example.txt') or its index
        :param open_as: Will open the file as the specified file type, overriding the automatic file type identification
        :return: The loaded content of the file - the type depends on the type of the file. None, when no matching file was found.
        """
        string_selection = None

        """
        Loading the file will only work, if a response has been received and the attachments were downloaded during the import.
        """
        if self._response is None:
            self._log("Response does not contain any data yet.", "USR")
            return None
        elif self._download_directory is None:
            self._log("No uploads were downloaded from the ELN API. Request downloads via the importer first.", "USR")
            return None
        elif self.get_attachments() is None and os.listdir(self._download_directory) == []:
            self._log("No uploads were attached to the response.", "USR")
            return None

        if type(selection) is str:
            string_selection = selection
        elif type(selection) is int:
            try:
                string_selection = self.get_attachments()[selection].real_name
            except IndexError:
                self._log("Error during attachment selection: index is out of range!", "USR")
                return None

        directory = self.get_download_directory()

        return self.__file_manager.open_file(directory + string_selection, open_as=open_as, **kwargs)

    def open_upload(self, selection: Union[str, int], open_as: str = None, **kwargs) -> Union[str, any, None]:
        return self.open_attachment(selection=selection, open_as=open_as, **kwargs)

    def extract_tables(self, output_format: Literal["list", "dataframes"] = "dataframes", reformat=True, reset=True, **kwargs):

        if reset:
            self._tables = []

        html_body = self._response["body"]

        if "decimal" in kwargs:
            decimal = kwargs["decimal"]
            kwargs.pop("decimal")
        else:
            decimal = "."

        if "force_numeric" in kwargs:
            force_numeric = kwargs["force_numeric"]
        else:
            force_numeric = False

        tables_pd = pd.read_html(StringIO(html_body), decimal=decimal, thousands=None)

        if reformat:
            tables_pd = self._reformat_tables(tables_pd, force_numeric=force_numeric)

        if output_format == "dataframes":
            self._tables = tables_pd
            return self._tables
        elif output_format == "list":
            for table in tables_pd:
                if reformat:
                    self._tables.append(table.data().values.tolist())
                else:
                    self._tables.append(table.values.tolist())
            return self._tables

    def _reformat_tables(self, tables: Union[list[pd.DataFrame], pd.DataFrame], force_numeric=False, null_value=None) -> Union[TabularData, list[TabularData]]:

        if type(tables) is list:
            conv_tables = []
            for table in tables:
                conv_tables.append(self._reformat_tables(table, force_numeric=force_numeric))
            return conv_tables

        converted_table = TabularData(data=tables)

        potential_header_command = tables.iloc[0, 0]

        if type(potential_header_command) is str and potential_header_command[0] == ".":
            converted_table._data = converted_table.data().drop(0)
            converted_table._data = converted_table.data().reset_index(drop=True)
            converted_table = self._interpret_header(tables.iloc[0, 0], converted_table)

        if tables.shape[1] != 2:
            headers = converted_table.data().iloc[[0]].values.tolist()[0]
            converted_table.set_headers(headers)
            converted_table.set_data(converted_table.data().drop(0))
            converted_table.set_data(converted_table.data().reset_index(drop=True))

            converted_table.convert_to_numeric(force=force_numeric, null_value=null_value)

        return converted_table

    @staticmethod
    def _interpret_header(command, table: TabularData) -> TabularData:

        commands = {"doo": ""}

        for cmd in commands:
            if cmd in command:
                print("ok")
                return table

        table.title = command[1:].strip()

        return table

    def return_table_as_pd(self, selection: Union[str, int]) -> pd.DataFrame:
        if type(selection) is int:
            try:
                return self._tables[selection].data()
            except IndexError:
                self._log("Error for selection: index is out of range!", "USR")
        else:
            for table in self._tables:
                if table.title == selection:
                    return table.data()

    def return_table(self, selection: Union[str, int]) -> pd.DataFrame:
        if type(selection) is int:
            try:
                return self._tables[selection]
            except IndexError:
                self._log("Error for selection: index is out of range!", "USR")
        else:
            for table in self._tables:
                if table.title == selection:
                    return table

    @property
    def tables(self):
        table_dict = {}
        for table in self._tables:
            table_dict[table.title] = table
        return table_dict

    def save_to_csv(self, file, index=None, **kwargs):

        file = file.replace(".csv", "")

        if index is None:
            for i, table in enumerate(self._tables):
                self.__file_manager.write_to_csv(f"{file}-{i+1}", table, **kwargs)
        else:
            self.__file_manager.write_to_csv(file, self._tables[index], **kwargs)

    # noinspection PyTypeChecker
    def save_to_json(self, path=None, **kwargs):

        self._response["requestTimeStamp"] = self.get_metadata("requestTimeStamp")

        with open(path, "w") as writefile:
            json.dump(self._response, writefile, **kwargs)

        self._log(f"wrote ELN entry to file: {path}", "FIL")

    def read_response_from_json(self, file, process=True):
        with open(file, "r") as readfile:
            response = json.load(readfile)

        self._response = response

        if process:
            self.extract_metadata()

    def load_dataset(self, json_file: str = None, download_directory: str = None, **kwargs):

        if download_directory is None:
            root = tk.Tk()
            root.update()
            download_directory = filedialog.askdirectory(initialdir=os.getcwd(),
                                                         title="Select directory where data is stored")
            root.destroy()

        if json_file is None:

            root = tk.Tk()
            root.update()
            json_file = filedialog.askopenfilename(initialdir=download_directory, title="Select experiment to load",
                                                   filetypes=[("JSON files", "*.json"), ("text files", "*.txt")])
            root.destroy()

        experiment_title = json_file[json_file.rfind("/") + 1:json_file.find("_ELNEntry")]

        self.read_response_from_json(json_file)
        self.set_download_directory(download_directory)

        if "decimal" in kwargs:
            decimal = kwargs["decimal"]
        else:
            decimal = "."

        self.extract_tables(decimal=decimal)

        self.add_metadata("short title", experiment_title)

        self._log("Imported dataset from file", "FIL")

    def as_dict(self,
                duplicate_handling: Literal["use first", "use last", "user selection", "raise error"] = "raise error"
                ) -> dict:
        """
        Returns a dict containing all metadata of the ELN response as well as key-value-pairs retrieved from the tables
        inside the main body.
        :param duplicate_handling: Defines behavior upon encountering multiple values for the same key. 'use last' uses
        the value given at the last occurrence of the key; 'use first' uses the value given at the first occurrence of
        the key; 'raise error' raises a value error; 'user selection' lets the user select the desired value via input()
        :return: Dict containing all retrievable key-value-type information about the experiment
        """

        eln_dict = self._metadata

        if self._tables is not None:
            eln_dict.update(self._get_dict_from_tables(duplicate_handling=duplicate_handling))

        return eln_dict

    def _get_dict_from_tables(self,
                              duplicate_handling: Literal["use last", "use first", "user selection", "raise error"]
                              = "raise error"
                              ) -> dict:
        """
        Retrieves key-value pairs from tables present in the ELN response.

        Only considers tables with two columns.
        :param duplicate_handling: Defines behavior upon encountering multiple values for the same key. 'use last' uses
        the value given at the last occurrence of the key; 'use first' uses the value given at the first occurrence of
        the key; 'raise error' raises a value error; 'user selection' lets the user select the desired value via input()
        :return: Dict containing all key-value pairs retrieved from the tables
        """
        table_dict = {}

        for table in self._tables:

            if table.width == 2:

                table_data = dict(table._data.values)

                for element in table_data:

                    if element not in table_dict:
                        table_dict[element] = table_data[element]

                    elif element in table_dict:
                        self._log(f"encountered duplicate metadata entry '{element}'", "WRN")

                        if duplicate_handling == "use last":
                            table_dict[element] = table_data[element]
                            self._log(f"value for '{element}' was overwritten", "WRN")

                        elif duplicate_handling == "use first":
                            self._log(f"using first value for '{element}'", "PRC")

                        elif duplicate_handling == "user selection":
                            self._log(f"please select value to use for {element}", "USR")
                            possibilities = [table_dict[element], table_data[element]]
                            self._log(f"0\t{possibilities[0]} (current)", "USR")
                            self._log(f"1\t{possibilities[1]} (from table '{table.title}')", "USR")
                            selection = self.input("select by index: ", input_type="int", value_range=(0, 1))
                            table_dict[element] = possibilities[selection]

                        elif duplicate_handling == "raise error":
                            raise ValueError(f"Encountered duplicate metadata entry '{element}'. "
                                             f"Specify argument 'duplicate_handling' to change the behavior.")

        return table_dict


class ELNImporter(ELNDataLogger):
    def __init__(self, api_key: str = None, url: str = None,
                 permissions: Literal["read only", "read and write"] = "read only",
                 silent: bool = False, debug: bool = False):
        """
        Handles importing ELN entries from eLabFTW by using the python API.
        :param api_key: Key to access the API
        :param url: URL to access the API
        :param permissions: Permissions of the API
        """

        super().__init__(debug, silent)

        self.api_key = api_key
        self.url = url
        self.permissions = permissions
        self.response = None
        self.working = None

        self.__file_manager = FileManager()

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
                read_attachments: bool = False, download_attachments: Union[bool, str] = False, return_http_response: bool=False
                ) -> Union[ELNResponse, list[ELNResponse], urllib3.response.HTTPResponse, None]:
        """
        Sends a request to the API and stores / returns the response
        :param query: Term to search for in the entry titles
        :param limit: Maximum amount of results returned by the response
        :param advanced_query: Element-value pair (i.e. 'id:1234') to filter response
        :param allow_list: If True, a list of ELNResponse objects is returned instead of asking the user to select one
        :param read_attachments: If True, all attached files of the ELN entry will be attached to the ELNResponse
        :param download_attachments: If True, all attachments will be downloaded
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
                                              extended=advanced_query.replace(" ", "").strip())
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

                if read_attachments or download_attachments:
                    self.response.extract_metadata()
                    self.request_attachments(self.response.id)

                if download_attachments and type(download_attachments) is bool:
                    self.download_attachments()
                elif download_attachments and type(download_attachments) is str:
                    self.download_attachments(directory=download_attachments)

            self.response.add_importer_log(self.log)

            return self.response

        except urllib3.exceptions.MaxRetryError:
            return None

    def request_attachments(self, identifier) -> list[Upload]:
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        self._log(f"requesting uploads for experiment with id {identifier}", "COM")

        uploadsApi = elabapi_python.UploadsApi(api_client)

        uploads: list[Upload] = uploadsApi.read_uploads("", identifier)

        self.response._attachments = uploads

        self._log(f"received {len(uploads)} uploads", "COM")

        return uploads

    def download_attachments(self, directory="Downloads/") -> None:

        directory = self.__file_manager.unify_directory(directory)

        for upload in self.response.get_attachments():
            upload_http = self._get_upload_from_api(upload, format="binary", _preload_content=False)

            self.__file_manager.write_data_to_file(upload_http.data, directory + upload.real_name, mode="wb")

        self.response._download_directory = self.__file_manager.get_absolute_path(directory)

        self._log(f"wrote {len(self.response.get_attachments())} uploads to directory: {self.response.get_download_directory()}", "FIL")

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
        object_selection = None

        if self.response is None:
            self._log("No data was received yet.", "USR")
            return None
        elif self.response.get_attachments() is None:
            self._log("No uploads were attached to the received response.", "USR")
            return None

        if type(selection) is str:
            string_selection = selection

        elif type(selection) is int:
            try:
                object_selection = self.response.get_attachments()[selection]
                string_selection = object_selection.real_name
            except IndexError:
                self._log("Error during attachment selection: index is out of range!", "USR")
                return None

        for upload in self.response.get_attachments():
            if upload.real_name == string_selection:
                object_selection = upload

        directory = self.response.get_download_directory()
        if directory is None:
            pass
        elif directory[-1] != "\\":
            directory += "\\"

        if directory is not None:
            return self.__file_manager.open_file(directory + string_selection)
        elif object_selection is not None:
            data = self._get_upload_from_api(object_selection, _preload_content=False, format="binary")
            with open("Downloads/temp/" + object_selection.real_name, "wb") as writefile:
                writefile.write(data.data)
            self._log(f"""generated temporary file '{"Downloads/temp/" + object_selection.real_name}'""", "FIL")
            re_read_data = self.__file_manager.open_file("Downloads/temp/" + object_selection.real_name)
            os.remove("Downloads/temp/" + object_selection.real_name)
            return re_read_data
        else:
            return None

    def _open_file(self, path, open_csv=True) -> Union[str, None]:

        filetype = self.__file_manager.analyze_filetype(path)

        if filetype == "csv" and open_csv:
            return self._open_csv(path)
        elif filetype in ["txt", "csv"]:
            with open(path, "r") as readfile:
                str_content = readfile.read()
            return str_content
        else:
            self._log(f"Filetype '{filetype}' is not supported yet!", "USR")
            return None

    def _open_csv(self, path, check=True, **kwargs):
        csv_data = pd.read_csv(path, **kwargs)
        if check:
            if csv_data.shape[1] == 1:
                self._log("CSV file seems to have only one column:", "USR")
                self._log(f"Example row: {csv_data[:1]}", "USR")
                self._log(f"Set delimiter and try again or type 'c' to continue", "USR")
                delimiter = input(">> ")
                if delimiter.strip() == "q":
                    return csv_data
                else:
                    csv_data = self._open_csv(path, check=True, delimiter=delimiter)
        return csv_data

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
        else:
            self._log(f"file '{file}' does not exist", "FIL")

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


def is_float(value):
    try:
        value = float(value)
    except ValueError:
        return False
    except TypeError:
        return False

    return True


def smart_request(experiment_id, api_file=None, api_url=None, experiment_title=None, download_directory=None,
                  save_to_json=True, download_attachments=True, debug=False, extract_tables=True) -> [ELNResponse, str]:
    importer = ELNImporter(silent=True, debug=debug)
    importer.attach_api_key_from_file(api_file)
    importer.configure_api(url=api_url, permissions="read only",
                           verify_communication=False)

    experiment = importer.request(advanced_query=f"id:{experiment_id}")

    if experiment_title is None:
        experiment_title = experiment.get_metadata("title").split(" ")[0]

    if download_directory is None:
        download_directory = "Downloads/" + experiment_title
        try:
            os.mkdir("./" + download_directory)
        except FileExistsError:
            importer._log(f"Directory '{download_directory}' already exists.", "FIL")
        except PermissionError:
            importer._log(f"Permission denied: Unable to create '{download_directory}'.", "USR")

    if download_attachments:
        experiment = importer.request(advanced_query=f"id:{experiment_id}", download_attachments=download_directory)

    if save_to_json:
        experiment.save_to_json(download_directory + "/" + experiment_title + "_ELNEntry.json")

    if extract_tables:
        experiment.extract_tables()

    experiment.add_metadata("short title", experiment_title)

    return experiment, download_directory


def example_of_use():
    importer = ELNImporter(debug=True)

    importer.attach_api_key_from_file(
        file="YOUR-API-KEY-FILE")
    importer.configure_api(url="YOUR-API-HOST-URL", permissions="read only")

    importer.ping_api()

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

