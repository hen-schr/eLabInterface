import json

import numpy as np
import scipy.optimize as opt
import matplotlib.pyplot as plt
import os
from typing import Literal, Union
import shutil
import re
from datetime import datetime
from tkinter import filedialog
import pandas as pd

module_version = 0.2


class DataManager:
    def __init__(self, template_file=None, working_directory=None, short_title=None, silent=False, debug=False):
        """
        This class is used to aid with data processing by logging processing steps and results, systematically naming generated files, creating automatic reports or bundling the dataset after the analysis.

        :param template_file: path to a template file, which can be used to generate automatic reports or readme files
        :param working_directory: directory where files are stored and read from by default
        :param short_title: a short title for the dataset which is prepended to generated file names
        :param silent: if true, no log messages will be displayed in the console
        :param debug: if true, all log messages are displayed in the console

        E.g., an instance of this class can be created in parallel to data processing using pandas (pd) or pyplot (plt) to enhance the analysis process:

        *manager = DataManager()*

        *plt.scatter(x, y)*

        *manager.savefig('sample_plt.png', comment='a simple example')*

        *df = pd.DataFrame((x, y))*

        *df.to_csv(manager.get_working_directory() + 'path-to-file.csv')*

        *manager.comment_file('path_to_file.csv', 'an example of csv type data')*

        *manager.generate_readme(readme_template='template-file.md')*
        """

        self.template_file: Union[str, None] = template_file
        self.file_comments: dict =  {"raw": "", "processed": ""}
        self.short_title: Union[str, None] = short_title
        self._summary: Union[str, None] = None
        self._caption_index: int = 1
        self._vocabulary: Union[dict, None] = None

        self._results: dict = {}

        self.log: str = ""
        self._silent: bool = silent
        self._debug: bool = debug

        self._working_directory: Union[str, None] = working_directory

        if self._working_directory is None:
            self._working_directory = os.getcwd()

        self._working_directory: str = self._harmonize_path(self._working_directory, path_type="directory", check_for_existence=True)

        if not os.path.exists(self._working_directory):
            raise FileNotFoundError(f"path {self._working_directory} does not exist!")

    @staticmethod
    def _harmonize_path(path, path_type: Literal["directory", "file"]="directory", check_for_existence=False) -> str:

        # working with unix-like filepaths
        harmonized_path = path.replace("\\", "/")

        # making sure paths add up correctly later on
        if path_type == "directory" and harmonized_path[-1] != "/":
            harmonized_path += "/"

        if check_for_existence and not os.path.exists(harmonized_path):
            raise FileNotFoundError(f"path {harmonized_path} does not exist!")

        return harmonized_path

    def _log(self, message: str, category: Literal["PRC", "FIL", "ERR", "WRN", "USR"] = None) -> None:
        """
        Logs important events of data processing and other activities.
        :param message: Message to add to the log, will be automatically timestamped
        :param category: PRC (processing), FIL (file system related), ERR (error), WRN (warning), USR (user message),
        """
        self.log += f"""\n{datetime.strftime(datetime.now(), "%y-%m-%d %H:%H:%S.%f")}""" \
                    + f"""\t{category if category is not None else "   "}\t{message}"""

        if (not self._silent and category == "USR") or self._debug:
            print(message)

    def set_caption_index(self, num: int):

        if type(num) is int:
            self._caption_index = num
        else:
            raise ValueError("Caption index must be int")

    def get_working_directory(self):
        return self._working_directory

    def set_working_directory(self, path):
        self._working_directory = self._harmonize_path(path, path_type="directory", check_for_existence=True)

    def get_summary(self):
        return self._summary

    def add_result(self, result_key: str, result_value: str, allow_replacement = True):
        if result_key not in self._results:
            self._results[result_key] = result_value

        elif result_key in self._results and allow_replacement:

            self._log(f"Replacing value {result_key}: {self._results[result_key]} -> {result_value}")
            self._results[result_key] = result_value

        else:
            raise KeyError(
                f"Result key {result_key} already exists! Pass 'allow_replacement=True' to overwrite existing values.")

    def print_results(self):
        for k, v in self._results.items():
            print(f"{k}: {v}")

    def generate_summary(self, dataset: Union[dict, any], desired_parameters: list[str],
                         handle_missing: Literal["raise", "ignore", "coerce"]="raise", separator: str="; ",
                         use_vocabulary=False) -> str:
        """
        Generates a summary string for the passed dataset.
        :param dataset: dict or dict-like object
        :param desired_parameters: parameters to extract from the dataset for the summary
        :param handle_missing:  'raise': KeyError is raised when desired parameter is missing;
                                'ignore': missing parameters are not added to the summary;
                                'coerce': missing values are set to None
        :param separator: character used to separate the parameters in the generated summary string
        :param use_vocabulary: if True, the summary is generated based on controlled vocabulary that can be added to the DataManager; see *add_vocabulary* for reference
        :return: Summary of dateset with parameters separated by the separator
        """

        display_parameters = {}

        for param in desired_parameters:
            try:
                display_parameters[param] = dataset[param]
            except KeyError:
                if handle_missing == "raise":
                    raise KeyError(f"Missing required parameter '{param}'")
                elif handle_missing == "ignore":
                    pass
                elif handle_missing == "coerce":
                    display_parameters[param] = None

        summary = ""

        for element, value in display_parameters.items():

            if use_vocabulary:

                if self._vocabulary is None:
                    self.add_vocabulary()

                summary += self._generate_param_value_string(element, value, extraction_method="json")

            else:

                summary += self._generate_param_value_string(element, value)

            summary += separator

        summary = summary[:-len(separator)]

        self._summary = summary

        return summary

    def _generate_param_value_string(self, element: str, value: any,
                                     extraction_method: Literal["string dissection", "json"]="string dissection") -> str:
        """
        Generates a string from an element-value pair that includes the value as well as the unit of the value, if specified in the element string.
        :param element: string describing the parameter, usually in the format 'name / unit'
        :param value: value to be converted to string
        :return: string of the value and potentially the unit

        Examples:
        _generate_param_value_string('time / min', 20) returns '20 min';
        _generate_param_value_string('name', 'sam') returns 'sam'
        """
        str_value = str(value)

        if is_float(value):
            unit = self._get_unit_for_parameter(element, extraction_method=extraction_method)
            if unit != "":
                str_value += " " + unit

        return str_value

    def _get_unit_for_parameter(self, parameter: str,
                                extraction_method: Literal["string dissection", "json"]="string dissection",
                                split_string: str=" / ") -> str:
        """
        Extracts the unit from a string of type "name-of-parameter / unit".

        :param parameter: string to extract the unit from
        :param extraction_method:  'string dissection': extracts units by interpreting the passed parameter string; 'json': (not implemented) extracts unit based on a json schema
        :param split_string: string to split the parameter string by when 'string dissection' is used
        :return: Unit as str
        """

        if extraction_method == "json":
            raise NotImplementedError("unit interpretation based on JSON vocabulary is not implemented yet")
        elif extraction_method == "string dissection":
            split_parameter = parameter.split(split_string, 1)
            unit = split_parameter[1] if len(split_parameter) == 2 else ""

            return unit

    def add_vocabulary(self, filepath=None, mode: Literal["overwrite", "append"]="overwrite") -> None:
        """
        Imports vocabulary that can be used to interpret data more easily.
        :param filepath: Path to a JSON file, if left empty, a tkinter filedialog is opened
        :param mode: defines action taken when another vocabulary set has been imported into the object already - 'overwrite': existing vocabulary is overwritten by the new dataset; 'append': existing vocabulary is extended by the new dataset
        :return: None

        format of a vocabulary file (*.json):

        {
            "unique-name-of-element": {"term": "number 1", "definition": "first example", "unit": "Hz"},
            "unique-name-of-second-element": {"term": "number 2", "definition": "second example", "unit": "m s-1"}
        }
        """

        if filepath is None:
            filepath = filedialog.askopenfilename(initialdir=self._working_directory,
                                                  filetypes=[("JSON files", "*.json"), ("text files", "*.txt")],
                                                  title="select vocabulary file")

        filepath = self._harmonize_path(filepath, "file", False)

        with open(filepath, "r") as readfile:
            vocabulary = json.load(readfile)

        self._check_vocabulary_structure()

        if self._vocabulary is None or mode == "overwrite":
            self._vocabulary = vocabulary
        elif mode == "append":
            self._vocabulary.update(vocabulary)

    def _check_vocabulary_structure(self):
        pass

    def write_dataframe_to_file(self, dataframe: pd.DataFrame, filename: str, directory: str = None,
                                comment: str = None, category: str = "processed", add_prefix=True, **kwargs):

        if add_prefix:
            filename = ((self.short_title + "_") if self.short_title is not None else "") + filename

        if directory is None:
            directory = self._working_directory
        if directory is None:
            directory = ""

        directory = self._harmonize_path(directory, "directory", True)

        if "sep" in kwargs:
            sep = kwargs["sep"]
            kwargs.pop("sep")
        else:
            sep = ";"
        if "decimal" in kwargs:
            decimal = kwargs["decimal"]
            kwargs.pop("decimal")
        else:
            decimal = ","

        dataframe.to_csv(directory + filename, sep=sep, decimal=decimal, **kwargs)

        self.comment_file(filename, comment, category=category)

    def savefig(self, filename: str, directory: str=None, comment: str=None, category: str="processed",
                generate_caption: bool=True, caption_offset: float=None, add_prefix=True, **kwargs) -> plt.Figure:
        """
        Saves the current pyplot figure. Comments and captions can be added to improve the documentation.

        :param filename: file to write the figure to, i.e. 'figure1.png'
        :param directory: directory to create the file in, e.g. 'plots/'; if left empty, the standard directory of the manager is used, or the current working directory
        :param comment: a description of the plot to add more context; can be used to generate readme files or other documentation later on
        :param category: category of the figure and comment, e.g. 'raw' or 'processed'; see *comment_file* for reference
        :param generate_caption: if true, a caption with the comment is added below the figure
        :param caption_offset: distance between the bottom edge of the plot and the generated caption
        :param kwargs: arguments passed to *pyplot.savefig*, see for reference
        :return: current figure without the caption
        """

        if add_prefix:
            filename = ((self.short_title + "_") if self.short_title is not None else "") + filename

        if directory is None:
            directory = self._working_directory
        if directory is None:
            directory = ""

        directory = self._harmonize_path(directory, "directory", True)

        fig = plt.gcf()

        plt.savefig(directory + filename, **kwargs)

        if generate_caption:

            if caption_offset is None:
                caption_offset = 0.05

            caption = f"Figure {self._caption_index}: {comment}"
            self._caption_index += 1

            fig.text(0.5, -caption_offset, caption, ha="center", wrap=True, va="top", multialignment="left")

        if comment is None:
            return fig

        self.comment_file(filename, comment, category=category)

        return fig

    def comment_file(self, filename, comment, category: Literal["raw", "processed"] = "processed"):

        comment_str = f"- `{filename}`: {comment}\n"

        self.file_comments[category] = self.file_comments[category] + comment_str

    def generate_readme(self, parameters: dict = None, path=None, readme_template=None):

        if parameters is None:
            parameters = {}

        for key, value in self.file_comments.items():
            parameters[f"{key}_file_comments"] = value.strip("\n")

        if readme_template is None:
            readme_template = self.template_file

        with open(readme_template, "r") as readfile:
            template = readfile.read()

        if path is None:
            path = self._working_directory + "README.md"

        for key, value in parameters.items():
            template = template.replace(f"%{key}%", str(value))

        with open(path, "w") as writefile:
            writefile.write(template)

    def generate_python_from_jupyter(self, notebook_path, script_path=None, assure_local_execution=True,
                                     pre_text: str = None):

        if not os.path.exists(notebook_path):
            notebook_path = self._working_directory + notebook_path
            if not os.path.exists(notebook_path):
                raise FileNotFoundError(f"file {notebook_path} does not exist!")

        working_directory = notebook_path[:notebook_path.rfind("/") + 1]

        notebook_name = notebook_path[notebook_path.rfind("/") + 1:].replace(".ipynb", "") + ".ipynb"

        if script_path is None:
            script_path = notebook_path.replace(".ipynb", "")
        else:
            script_path = script_path.replace(".py", "")

        if script_path[:len(working_directory)] == working_directory:
            script_path = script_path.replace(working_directory, "")

        self._log(f"converting jupyter notebook '{notebook_name}' to python script...", "PRC")
        wd = os.getcwd()
        os.chdir(working_directory)
        os.system(f"""jupyter nbconvert --to script "{notebook_name}" --output "{script_path}" --log-level=ERROR""")
        os.chdir(wd)

        self._log(f"processing generated script...", "PRC")
        with open(working_directory + script_path + ".py", "r") as readfile:
            script_str = readfile.read()

        script_end = script_str.find("%script end%")
        script_str = script_str[:script_end]

        if pre_text is not None:
            script_str = pre_text + script_str

        if assure_local_execution:
            local_code = """
# make sure that the script is always executed in the same directory as where the script itself is stored
import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

"""

            script_str = local_code + script_str

        with open(working_directory + script_path + ".py", "w") as writefile:
            writefile.write(script_str)

        self._log(f"successfully created python script at '{script_path}'", "PRC")

    def generate_archive(self, path=None, file_list=None, notebook_name=None, script_location=None,
                         file_filter: str = None, jupyter_to_script=True,
                         include_code: Literal["full", "installscript"] = "full", to_zip=True):
        if path is None:
            path = self._working_directory + self.short_title + "_archive/"

        if file_list is None:
            file_list = os.listdir(self._working_directory)

        if not os.path.exists(path):
            os.mkdir(path)
        if not os.path.exists(path + "/Lib/"):
            os.mkdir(path + "/Lib/")

        if notebook_name is None:
            notebook_name = self.short_title + ".ipynb"

        notebook_path = os.getcwd().replace("\\", "/") + "/" + notebook_name.replace(".ipynb", "") + ".ipynb"

        shutil.copy(notebook_path, path + self.short_title + ".ipynb")
        self._log("copied jupyter notebook", "FIL")

        if jupyter_to_script:
            self.generate_python_from_jupyter(path + self.short_title + ".ipynb")

        copied_files = 0

        for file in file_list:
            if os.path.isdir(self._working_directory + file):
                pass
            elif file_filter is None:
                shutil.copy(self._working_directory + file, path + file)
                copied_files += 1
            elif re.search(file_filter, file) is not None:
                shutil.copy(self._working_directory + file, path + file)
                copied_files += 1

        self._log(f"copied {copied_files} data files", "FIL")

        if include_code == "full":
            if script_location is None:
                script_location = os.getcwd().replace("\\", "/") + "/Lib/"
            self._copy_scripts(script_location, path + "/Lib/")
        elif include_code == "installscript":
            print("Generating install scripts has not been implemented yet.")

        if to_zip:
            shutil.make_archive(path[:-1], "zip", path)
            shutil.rmtree(path)
            self._log("created zip archive with all data concerning the experiment", "FIL")

        else:
            self._log("created archive with all data concerning the experiment", "FIL")

    def _copy_scripts(self, origin_directory, target_directory):
        files = os.listdir(origin_directory)

        copied_files = 0

        for file in files:
            if file[-3:] == ".py":
                shutil.copy(origin_directory + file, target_directory + file)
                copied_files += 1

        self._log(f"copied {copied_files} scripts", "FIL")


class ProcessingStep:
    def __init__(self, title=None, comment=None, params: dict = None):
        self.step = title
        self.comment = comment
        self.params = params

    def __str__(self):

        step_string = f"{self.step}\n\t"
        step_string += f"{self.comment}\n\t" if self.comment is not None else ""

        for par, val in self.params.items():
            step_string += f"- {par}: {val}\n\t"

        step_string = step_string[:-2]

        return step_string


class DataProcessor:
    def __init__(self, proc_type: str = None):
        self.steps: list[ProcessingStep] = []
        self.proc_type = proc_type

    def _add_step(self, title, comment=None, params=None):
        self.steps.append(ProcessingStep(title=title, comment=comment, params=params))

    def __str__(self):
        step_string = ""

        for i, step in enumerate(self.steps):
            step_string += f"{i + 1}. {str(step)}\n"

        return step_string

    def linear(self, x, m, c=0) -> float:
        self._add_step("Linear equation", comment="y = mx + c", params={"m": m, "c": c})

        y = x * m + c

        return y


def return_slice_of_data(x, y, interval):

    actual_interval = [0, 0]

    if interval[1] is None:
        #TODO should be changed to x_stop = -1 later
        interval[1] = -0.000001
    
    for i, num in enumerate(interval):
        if num < 0:
            actual_interval[i] = np.max(x) + num
        else:
            actual_interval[i] = num
    
    x_start = None
    x_stop = None
    for i, x_i in enumerate(x):
        if x_i >= actual_interval[0] and x_start is None:
            x_start = i
        elif x_i >= actual_interval[1] and x_stop is None:
            x_stop = i
        if x_stop is not None:
            break
    
    data_slice_x = x[x_start:x_stop]
    data_slice_y = y[x_start:x_stop]
        
    return data_slice_x, data_slice_y
    
    
def inverted_polynome(y, a, b, c=0):
    x = (- b + np.sqrt(b**2 - 4 * a * (c - y))) / (2 * a)
    return x


def polynome(x, a, b, c):
    y = a*x**2 + b * x + c
    return y
    

def linear(x, m, c=0):
    y = m * x + c
    return y


def orig_linear(x, m):
    y = linear(x, m)
    return y


def generate_readme(parameters, path, readme_template="README.md"):
    with open(readme_template, "r") as readfile:
        template = readfile.read()

    for key, value in parameters.items():
        template = template.replace(f"%{key}%", str(value))

    with open(path, "w") as writefile:
        writefile.write(template)


def savefig(directory, filename, comment=None, comment_file=None, **kwargs):

    if directory[-1] != "/":
        directory += "/"

    plt.savefig(directory + filename, **kwargs)

    if comment_file is None:
        comment_file = directory + "file_comments.temp"

    if comment is not None:
        comment_str = f"- `{filename}`: {comment}\n"
        with open(comment_file, "a") as writefile:
            writefile.write(comment_str)


def clear_comment_file(directory, filename="file_comments.temp"):

    if directory[-1] != "/":
        directory += "/"

    if os.path.exists(directory + filename):
        os.remove(directory + filename)


def comment_file(filename, comment, comment_file="file_comments.temp"):

    comment_str = f"- `{filename}`: {comment}\n"
    with open(comment_file, "a") as writefile:
        writefile.write(comment_str)


def is_float(value):
    try:
        value = float(value)
    except ValueError:
        return False
    except TypeError:
        return False

    return True


<<<<<<<< HEAD:data_processing.py
def calculate_averages_over_pressure(pressures, permeate_fluxes):
    unified_pressures = []
    unified_permeate_fluxes = []

    for i, pressure in enumerate(pressures):
        if pressure not in unified_pressures:
            unified_pressures.append(pressure)
            unified_permeate_fluxes.append([permeate_fluxes[i]])
        elif pressure in unified_pressures:
            p_index = unified_pressures.index(pressure)
            unified_permeate_fluxes[p_index].append(permeate_fluxes[i])

    unified_averages = []
    unified_stds = []

    for i, fluxes in enumerate(unified_permeate_fluxes):
        average = np.mean(fluxes)
        std = np.std(fluxes)

        unified_averages.append(average)
        unified_stds.append(std)

    return unified_pressures, unified_averages, unified_stds


def calculate_permeate_fluxes(x, y, intervals, pressures, average_of_last_min=10, plot=True):
    averages = []
    stds_flux = []

    if plot:
        plt.plot(x, y)
        ax = plt.gca()

    for j, interval in enumerate(intervals):
        x_start = None
        x_stop = None
        x_average = None
        for i, x_i in enumerate(x):
            if x_i >= interval[0] and x_start is None:
                x_start = i
            elif x_i >= interval[1] and x_stop is None:
                x_stop = i

        data_slice_x = x[x_start:x_stop]
        data_slice_y = y[x_start:x_stop]

        limit = np.max(data_slice_x) - average_of_last_min

        for i, x_i in enumerate(data_slice_x):
            if x_i >= limit:
                x_average = i
                break

        average = np.mean(data_slice_y[x_average:x_stop])
        std = np.std(data_slice_y[x_average:x_stop])
        averages.append(average)
        stds_flux.append(std)

        if plot:
            plt.plot(data_slice_x, data_slice_y, label=f"{pressures[j]} bar")
            plt.plot(data_slice_x[x_average:x_stop], data_slice_y[x_average:x_stop], color="r")

    return averages, stds_flux


def convert_raw_flux_data(data: pd.DataFrame, effective_membrane_area: float, time_format: str = "%H:%M:%S,%f",
                          reference_time: Union[str, datetime] = None,
                          index_time_column: int = 0, index_flow_rate: int = 1,
                          flow_rate_unit: Literal["mL min-1", "L h-1"] = "mL min-1"):

    if flow_rate_unit not in ["mL min-1", "L h-1"]:
        raise NotImplementedError("Function can currently only convert values given in 'mL min-1' or 'L h-1'")

    data["time"] = pd.to_datetime(data.iloc[:, index_time_column], format=time_format)

    if reference_time is None:
        reference_time = data["time"].iloc[0]
    elif type(reference_time) is str:
        reference_time = datetime.strptime(reference_time, time_format)

    # converting to relative time by subtracting the first entry in column 'time / min' from all lines
    data["time / min"] = (data["time"] - reference_time)
    data["time / min"] = data["time / min"].apply(lambda i: i.total_seconds() / 60)

    if flow_rate_unit == "mL min-1":
        conversion_factor_to_LMH = 60 / 1000 / effective_membrane_area
    elif flow_rate_unit == "L h-1":
        conversion_factor_to_LMH = 1 / effective_membrane_area
    else:
        raise NotImplementedError("Function can currently only convert values given in 'mL min-1'")

    data["flux / LMH"] = data.iloc[:, index_flow_rate] * conversion_factor_to_LMH

    return data


def fit_permeability(x, y, yerr=None, xerr=None, plot=False):
    print(x)

    optimized_parameters, pcov = opt.curve_fit(orig_linear, x, y)
    permeability = optimized_parameters[0]

    permeability_err = pcov[0, 0]
    errors = permeability_err

    if plot:
        plt.errorbar(x, y, yerr=yerr, xerr=xerr, fmt="o", ecolor="black", capsize=2)
        ax = plt.gca()
        ax.set_ylim([0, None])
        ax.set_xlim([0, None])
        ax.set_ylabel("Permeate Flux / $L \\; m^{-2} \\; h^{-1}$")
        ax.set_xlabel("Pressure / $bar$")
        resolved_x = np.linspace(0, max(x) * 1.1, 100)
        plt.text(0.01, 0.95, f"Permeability = {permeability:.2f} $LMH \\; bar" + "^{-1}$", transform=ax.transAxes)
        plt.plot(resolved_x, linear(np.asarray(resolved_x), *optimized_parameters))

    return permeability, errors


========
>>>>>>>> origin/master:data_processing/data_processing.py
calibration_dict = {
    "2nd order polynome": polynome,
    "inverted polynome": inverted_polynome,
    "linear": linear
}