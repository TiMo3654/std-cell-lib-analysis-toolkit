import numpy as np
from .util import *
import pandas as pd


def identify_switch_pin(df : pd.DataFrame) -> str:

    pins = [p for p in list(df.columns) if (len(p) == 1 or len(p) == 2)]

    for p in pins:

        diff = df[p].head(5).reset_index(drop=True) - df[p].tail(5).reset_index(drop=True)

        if diff.mean() != 0:

            break

    return p  


def calculate_tran_delay(df : pd.DataFrame, switch_pin : str) -> np.float64:

    time        = df['time'].to_numpy()
    sig_out     = df['Q'].to_numpy()
    sig_in      = df[switch_pin].to_numpy()

    threshold_point = 0.5 * np.max(sig_in)

    out_idx    = np.argmin(np.abs(sig_out - threshold_point))
    in_idx     = np.argmin(np.abs(sig_in - threshold_point))

    return time[out_idx] - time[in_idx]


def read_results(path_to_files : str) -> list:

    cells           = []

    result_files    = get_file_names(path_to_files)

    cell_names      = list(set([file.split('_')[0] for file in result_files]))

    for name in cell_names:

        cell_files  = [file for file in result_files if file.startswith(name)]

        transitions = []

        for file in cell_files:

            df        = pd.read_pickle(path_to_files + file)

            switch_pin  = identify_switch_pin(df)

            transitions.append(calculate_tran_delay(df, switch_pin))

        cells.append((name, np.min(transitions), np.max(transitions), np.mean(transitions)))      

    return cells