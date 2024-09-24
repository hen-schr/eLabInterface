from typing import Union, Literal
import elabapi_python
from elabapi_python.rest import ApiException
from tkinter import filedialog
import os


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

    def convert_to_markdown(self) -> str:
        pass

    def extract_metadata(self):
        self.metadata = {}
        self.identify_experiment_type()

    def identify_experiment_type(self):
        experiment_type = "unknown"
        self.metadata["experimentType"] = experiment_type

    def extract_tables(self) -> list[list]:
        pass

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

    def request(self, query=None, limit=None) -> Union[ELNResponse, None]:
        helper = HelperElabftw(self.api_key, self.url)
        api_client = helper.api_client

        items = elabapi_python.ItemsApi(api_client)

        items_list = items.read_items(limit=limit)

        if items_list is None:
            return None

        selection = items_list[0]

        response = ELNResponse(response=selection)

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

        return self.working



