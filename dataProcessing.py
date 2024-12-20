import numpy as np
import matplotlib.pyplot as plt
import os
from typing import Literal, Union

module_version = 0.1


class ProcessingLogger:
    def __init__(self, template=None, directory=None, prefix=None):
        self.template = template
        self.file_comments =  {"raw": "", "processed": ""}
        self.directory = directory
        self.prefix = prefix

        if self.directory[-1] != "/":
            self.directory += "/"

    def savefig(self, filename, directory=None, comment=None, category="processed", **kwargs):

        filename = ((self.prefix + "_") if self.prefix is not None else "") + filename

        if directory is None:
            directory = self.directory
        if directory is None:
            directory = ""

        if directory[-1] != "/":
            directory += "/"

        plt.savefig(directory + filename, **kwargs)

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


calibration_dict = {
    "2nd order polynome": polynome,
    "inverted polynome": inverted_polynome,
    "linear": linear
}