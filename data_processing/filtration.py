import scipy.optimize as opt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from data_processing import linear, polynome, inverted_polynome, calibration_dict, DataProcessor
from typing import Union, Literal
from datetime import datetime


class PermeateProcessor(DataProcessor):
    def __init__(self, proc_type: str = "permeate flux", data: pd.DataFrame = None):
        super().__init__(proc_type)
        self._original_data = data
        self.data = data
        self.data_origin = None

    def add_data(self, data: pd.DataFrame):
        self._original_data = data
        self.data = data

    def convert_raw_flux_data(self, effective_membrane_area: float, time_format: str = "%H:%M:%S,%f",
                              reference_time: Union[str, datetime] = None,
                              index_time_column: int = 0, index_flow_rate: int = 1,
                              flow_rate_unit: Literal["mL min-1", "L h-1"] = "mL min-1"):

        if flow_rate_unit not in ["mL min-1", "L h-1"]:
            raise NotImplementedError("Function can currently only convert values given in 'mL min-1' or 'L h-1")

        self.data["time"] = pd.to_datetime(self.data.iloc[:, index_time_column], format=time_format)

        if reference_time is None:
            reference_time = self.data["time"].iloc[0]
        elif type(reference_time) is str:
            reference_time = datetime.strptime(reference_time, time_format)

        # converting to relative time by subtracting the first entry in column 'time / min' from all lines
        self.data["time / min"] = (self.data["time"] - reference_time)
        self.data["time / min"] = self.data["time / min"].apply(lambda i: i.total_seconds() / 60)

        if flow_rate_unit == "mL min-1":
            conversion_factor_to_LMH = 60 / 1000 / effective_membrane_area
        elif flow_rate_unit == "L h-1":
            conversion_factor_to_LMH = 1 / effective_membrane_area
        else:
            raise NotImplementedError("Function can currently only convert values given in 'mL min-1'")

        self.data["flux / LMH"] = self.data.iloc[:, index_flow_rate] * conversion_factor_to_LMH

        self._add_step("Raw data conversion", "Converts volumetric flow rate to L m-2 h-1",
                       params={
                           "reference time": reference_time,
                           "time format": time_format,
                           "flow rate unit": flow_rate_unit})

        return self.data


def calculate_averages_over_pressure(pressures, permeate_fluxes) -> tuple[list[float], list[float], list[float]]:
    """
    Calculates the average and stddev of values recorded at the same pressure
    """

    unified_pressures, unified_averages, unified_stds = merge_values_of_same_x_value(pressures, permeate_fluxes)

    return unified_pressures, unified_averages, unified_stds


def merge_values_of_same_x_value(x_values: list[Union[int, float]], y_values: list[Union[int, float]]
                                )-> tuple[list[float], list[float], list[float]]:
    """
    Calculates the average and standard deviation of y values at the same x value.
    :param x_values: The y values at identical x values will be merged. Must have the same length as y_values
    :param y_values: These values will be merged if the x values are identical. Must have the same length as x_values
    :return: A 2D list with the unified axis_values, the average and stddev at each axis_value
    """

    if len(x_values) != len(y_values):
        raise ValueError(
            f"Axis values and values must have the same length but have different lengths "
            f"({len(x_values)}, {len(y_values)}).")

    unified_x_values = []
    unified_y_values = []

    for i, value in enumerate(x_values):
        if value not in unified_x_values:
            unified_x_values.append(value)
            unified_y_values.append([y_values[i]])
        elif value in unified_x_values:
            p_index = unified_x_values.index(value)
            unified_y_values[p_index].append(y_values[i])

    unified_y_averages = []
    unified_y_stds = []

    for i, fluxes in enumerate(unified_y_values):
        average = np.mean(fluxes)
        std = np.std(fluxes)

        unified_y_averages.append(average)
        unified_y_stds.append(std)

    return unified_x_values, unified_y_averages, unified_y_stds


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

    if flow_rate_unit == "mL min-1":
        raise NotImplementedError("Function can currently only convert values given in 'mL min-1'")

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

    optimized_parameters, pcov = opt.curve_fit(linear, x, y)
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