from typing import Union, Literal


class ELNResponse:
    def __init__(self):
        self.response = None
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

    def request(self) -> ELNResponse:
        pass

    def configure_api(self, api_key=None, url=None, permissions: Literal["read only", "read and write"] = "read only"):
        if api_key is not None:
            self.api_key = api_key
        if url is not None:
            self.url = url

        self.permissions = permissions

        self.ping_api()

    def ping_api(self) -> bool:
        """
        Test if the API could be reached with the defined configuration.
        :return: True if communication to API was successful, False if not
        """
        ping = False

        return ping



