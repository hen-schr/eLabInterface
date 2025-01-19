import scipy.optimize as opt
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from data_processing import linear, polynome, inverted_polynome, calibration_dict
from typing import Union, Literal
from datetime import datetime


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