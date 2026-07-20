from itertools import chain, repeat
from . import consts

__all__ = ('get_default_border_size', 'get_border', 'get_symbol_size',
           'check_valid_scale', 'check_valid_border', 'matrix_to_lines',
           'matrix_iter', 'matrix_iter_verbose')


def get_default_border_size(matrix_size):
    pass


def get_border(matrix_size, border):
    pass


def get_symbol_size(matrix_size, scale=1, border=None):
    pass


def check_valid_scale(scale):
    pass


def check_valid_border(border):
    pass


def matrix_to_lines(matrix, x, y, incby=1):
    pass


def matrix_iter(matrix, matrix_size, scale=1, border=None):
    pass


def matrix_iter_verbose(matrix, matrix_size, scale=1, border=None):
    pass
