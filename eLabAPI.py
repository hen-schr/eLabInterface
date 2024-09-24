from typing import Union, Literal
import elabapi_python
from elabapi_python.rest import ApiException
from tkinter import filedialog
import os
import json
import markdownify


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
        self.response = response
        self.metadata = {}
        self.tables = None

    def __str__(self):
        if self.response is not None:
            string = json.dumps(self.response, indent=4)

            return string
        else:
            return self

    def convert_to_markdown(self) -> Union[str, None]:
        if self.response is None:
            print("No response available to convert to markdown - request data first!")
            return None
        md_body = markdownify.markdownify(self.response["body"])

        return md_body

    def extract_metadata(self):
        self.metadata = {}
        self.identify_experiment_type()

    def identify_experiment_type(self):
        experiment_type = "unknown"
        self.metadata["experimentType"] = experiment_type

    def extract_tables(self) -> list[list]:
        md_body = self.convert_to_markdown()

        md_lines = md_body.split("\n")

        tables = []

        table_started = False

        # when the first line of a table is detected, all subsequent table lines are appended to the same sublist
        for line in md_lines:
            if len(line) == 0:
                pass
            elif line[0] == "|" and not table_started:
                table_started = True
                tables.append([list_from_string(line, separator="|")])
            elif line[0] == "|" and table_started:
                tables[-1].append(list_from_string(line, separator="|"))
            else:
                table_started = False

        print(f"Extracted {len(tables)} table(s)")

        return tables

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
ELNImporter class ({self.permissions})
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
