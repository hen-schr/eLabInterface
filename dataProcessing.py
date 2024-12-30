import numpy as np
import matplotlib.pyplot as plt
import os
from typing import Literal, Union
import shutil
import re

from fontTools.unicodedata import script
from scipy.optimize import direct

module_version = 0.1


class DataManager:
    def __init__(self, template=None, directory=None, prefix=None):
        self.template = template
        self.file_comments =  {"raw": "", "processed": ""}
        self.directory = directory
        self.prefix = prefix
        self.caption_index = 1
        self.summary = None

        if self.directory[-1] != "/":
            self.directory += "/"

    def generate_summary(self, data: Union[dict, any], summary_parameters: list[str], handle_missing: Literal["raise", "ignore", "coerce"]="raise") -> str:

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
            info_display += parameters[param]
            info_display += (" " + param.split(" / ")[-1].strip()) if is_float(
                parameters[param]) and "/" in param else ""
            info_display += "; "

        info_display = info_display[:-2]

        self.summary = info_display

        return info_display

    def savefig(self, filename, directory=None, comment=None, category="processed", generate_caption=True, caption_offset=None, **kwargs):

        filename = ((self.prefix + "_") if self.prefix is not None else "") + filename

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

            caption = f"Figure {self.caption_index}: {comment}"
            self.caption_index += 1

            fig.text(0.5, -caption_offset, caption, ha="center", wrap=True, va="top", multialignment="left")


        if comment is None:
            return True

        comment_str = f"- `{filename}`: {comment}\n"

        self.file_comments[category] = self.file_comments[category] + comment_str

    def comment_file(self, filename, comment, category: Literal["raw", "processed"] = "processed"):

        comment_str = f"- `{filename}`: {comment}\n"

        self.file_comments[category] = self.file_comments[category] + comment_str

    def generate_readme(self, parameters: dict, path=None, readme_template=None):

        for key, value in self.file_comments.items():
            parameters[f"{key}_file_comments"] = value

        if readme_template is None:
            readme_template = self.template

        with open(readme_template, "r") as readfile:
            template = readfile.read()

        if path is None:
            path = self.directory + "README.md"

        for key, value in parameters.items():
            template = template.replace(f"%{key}%", str(value))

        with open(path, "w") as writefile:
            writefile.write(template)

    @staticmethod
    def generate_python_from_jupyter(notebook_name, directory=None):

        if directory is None:
            directory = os.getcwd().replace("\\", "/") + "/"

        notebook_name = notebook_name.replace(".ipynb", "") + ".ipynb"
        script_path = directory + notebook_name.replace(".ipynb", "") + ".py"

        print(directory, notebook_name)

        os.system(f"""cd '{directory}'& jupyter nbconvert --to script {notebook_name}""")

        with open(script_path, "r") as readfile:
            script_str = readfile.read()

        script_end = script_str.find("%script end%")
        script_str = script_str[:script_end]

        with open(script_path, "w") as writefile:
            writefile.write(script_str)

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

        if jupyter_to_script:
            self.generate_python_from_jupyter(path + self.prefix + ".ipynb")
            #os.system(f"""jupyter nbconvert --to script {path + self.prefix + ".ipynb"}""")


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

        print(f"copied {copied_files} files")

        if include_code == "full":
            if script_location is None:
                script_location = os.getcwd().replace("\\", "/") + "/Lib/"
            print(script_location)
            self._copy_scripts(script_location, path + "/Lib/")
        elif include_code == "installscript":
            print("Generating install scripts has not been implemented yet.")

        if to_zip:
            shutil.make_archive(path[:-1], "zip", path)
            shutil.rmtree(path)


    @staticmethod
    def _copy_scripts(origin_directory, target_directory):
        files = os.listdir(origin_directory)

        copied_files = 0

        for file in files:
            if file[-3:] == ".py":
                shutil.copy(origin_directory + file, target_directory + file)
                copied_files += 1

        print(f"copied {copied_files} scripts")


def return_slice_of_data(x, y, interval):

    actual_interval = [0, 0]

    if interval[1] is None:
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

    return True


calibration_dict = {
    "2nd order polynome": polynome,
    "inverted polynome": inverted_polynome,
    "linear": linear
}