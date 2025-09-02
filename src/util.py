from liberty.parser import parse_liberty
from liberty.types import *
import numpy as np
import pandas as pd
import itertools
import re


# Helper functions

def convert_attributes(attribute : str):

    try:

        return float(attribute)

    except ValueError:

        return attribute
        

def attribute2dict(cell_attributes : Attribute) -> dict:

    s = [str(a) for a in cell_attributes]

    return {k.strip() : convert_attributes(v.strip()) for k, v in (item.split(':', 1) for item in s)}


def lib2list(library : Group) -> list:

    return [(str(cell_group.args[0]), attribute2dict(cell_group.attributes)) for cell_group in library.get_groups('cell')]


# Functions to preprocess given liberty files 

def preprocess_expression(expr):
    expr = re.sub(r'!', 'not ', expr)
    expr = re.sub(r'\+', ' or ', expr)
    expr = re.sub(r'\*', ' and ', expr)
    return expr

def extract_variables(expr):
    """
    Extracts unique variable names from a Boolean expression.
    Supports multi-letter names like IN1, CLK, data_ready.
    """
    # Remove operators and parentheses to isolate variables
    cleaned_expr = re.sub(r'[+\-*/^~!() ]', ' ', expr)
    tokens = re.findall(r'\b[A-Za-z_]\w*\b', cleaned_expr)
    return sorted(set(tokens))

def evaluate(expr, inputs):
    """Evaluates the Boolean expression with given inputs."""
    local_vars = {var: bool(val) for var, val in inputs.items()}
    try:
        return eval(expr, {}, local_vars)
    except Exception as e:
        raise ValueError(f"Error evaluating expression: {e}")
    
