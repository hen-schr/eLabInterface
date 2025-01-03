import numpy as np
import matplotlib.pyplot as plt
import os
from typing import Literal, Union
import shutil
import re
from datetime import datetime

module_version = 0.1


class DataManager:
    def __init__(self, template_file=None, directory=None, short_title=None, silent=False, debug=False):

        self.template_file = template_file
        self.file_comments =  {"raw": "", "processed": ""}
        self.directory = directory.replace("\\", "/") if type(directory) is str else directory
        self.short_title = short_title
        self._caption_index = 1
        self.summary = None

        self.log = ""
        self._silent = silent
        self._debug = debug

        if self.directory is None:
            self.directory = os.getcwd().replace("\\", "/")
        if self.directory[-1] != "/":
            self.directory += "/"

        if not os.path.exists(self.directory):
            raise FileNotFoundError(f"path {self.directory} does not exist!")

    def _log(self, message: str, category: Literal["PRC", "FIL", "ERR", "WRN", "USR"] = None) -> None:
        """
        Logs important events of data processing and other activities
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

    def generate_summary(self, data: Union[dict, any], summary_parameters: list[str],
                         handle_missing: Literal["raise", "ignore", "coerce"]="raise") -> str:

        parameters = {}

        for param in summary_parameters:
            try:
                parameters[param] = data[param]
            except KeyError:
                if handle_missing == "raise":
                    raise KeyError(f"Missing required parameter '{param}'")
                elif handle_missing == "ignore":
                    pass
                elif handle_missing == "coerce":
                    parameters[param] = None

        info_display = ""

        for param in parameters:
            info_display += str(parameters[param])
            info_display += (" " + param.split(" / ")[-1].strip()) if is_float(
                parameters[param]) and "/" in param else ""
            info_display += "; "

        info_display = info_display[:-2]

        self.summary = info_display

        return info_display

    def savefig(self, filename, directory=None, comment=None, category="processed", generate_caption=True, caption_offset=None, **kwargs):

        filename = ((self.short_title + "_") if self.short_title is not None else "") + filename

        if directory is None:
            directory = self.directory
        if directory is None:
            directory = ""

        if directory[-1] != "/":
            directory += "/"

        fig = plt.gcf()

        plt.savefig(directory + filename, **kwargs)

        if generate_caption:

            if caption_offset is None:
                caption_offset = 0.05

            caption = f"Figure {self._caption_index}: {comment}"
            self._caption_index += 1

            fig.text(0.5, -caption_offset, caption, ha="center", wrap=True, va="top", multialignment="left")


        if comment is None:
            return True

        comment_str = f"- `{filename}`: {comment}\n"

        self.file_comments[category] = self.file_comments[category] + comment_str

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
            path = self.directory + "README.md"

        for key, value in parameters.items():
            template = template.replace(f"%{key}%", str(value))

        with open(path, "w") as writefile:
            writefile.write(template)

    def generate_python_from_jupyter(self, notebook_path, script_path=None):

        if not os.path.exists(notebook_path):
            notebook_path = self.directory + notebook_path
            if not os.path.exists(notebook_path):
                raise FileNotFoundError(f"file {notebook_path} does not exist!")


        working_directory = notebook_path[:notebook_path.rfind("/") + 1]

        notebook_name = notebook_path[notebook_path.rfind("/") + 1:].replace(".ipynb", "") + ".ipynb"

        if script_path is None:
            script_path = notebook_path.replace(".ipynb", "") + ".py"
        else:
            script_path = script_path.replace(".py", "")

        if script_path[:len(working_directory)] == working_directory:
            script_path = script_path.replace(working_directory, "")


        self._log(f"converting jupyter notebook '{notebook_name}' to python script...", "PRC")
        os.system(f"""cd {working_directory} & jupyter nbconvert --to script {notebook_name} --output {script_path}""")

        self._log(f"processing generated script...", "PRC")
        with open(working_directory + script_path + ".py", "r") as readfile:
            script_str = readfile.read()

        script_end = script_str.find("%script end%")
        script_str = script_str[:script_end]

        with open(working_directory + script_path + ".py", "w") as writefile:
            writefile.write(script_str)

        self._log(f"successfully created python script at '{script_path}'", "PRC")

    def generate_archive(self, path=None, file_list=None, notebook_name=None, script_location=None,
                         file_filter: str = None, jupyter_to_script=True,
                         include_code: Literal["full", "installscript"] = "full", to_zip=True):
        if path is None:
            path = self.directory + self.prefix + "_archive/"

        if file_list is None:
            file_list = os.listdir(self.directory)

        if not os.path.exists(path):
            os.mkdir(path)
        if not os.path.exists(path + "/Lib/"):
            os.mkdir(path + "/Lib/")

        if notebook_name is None:
            notebook_name = self.prefix + ".ipynb"

        notebook_path = os.getcwd().replace("\\", "/") + "/" + notebook_name.replace(".ipynb", "") + ".ipynb"

        shutil.copy(notebook_path, path + self.prefix + ".ipynb")
        self._log("copied jupyter notebook", "FIL")

        if jupyter_to_script:
            self.generate_python_from_jupyter(path + self.prefix + ".ipynb")


        copied_files = 0

        for file in file_list:
            if os.path.isdir(self.directory + file):
                pass
            elif file_filter is None:
                shutil.copy(self.directory + file, path + file)
                copied_files += 1
            elif re.search(file_filter, file) is not None:
                shutil.copy(self.directory + file, path + file)
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
    

def linear(x, m, c):
    y = m * x + c
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


calibration_dict = {
    "2nd order polynome": polynome,
    "inverted polynome": inverted_polynome,
    "linear": linear
}