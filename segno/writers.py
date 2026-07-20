import io
import re
import zlib
import codecs
import base64
import gzip
from xml.sax.saxutils import quoteattr, escape
from struct import pack
from itertools import chain, repeat
import functools
from functools import partial
from functools import reduce
from operator import itemgetter
from contextlib import contextmanager
from collections import defaultdict
import time
from . import consts
from .utils import matrix_to_lines, get_symbol_size, get_border, \
    check_valid_scale, check_valid_border, matrix_iter, matrix_iter_verbose
from itertools import zip_longest
from urllib.parse import quote

__all__ = ('writable', 'write_svg', 'write_png', 'write_eps', 'write_pdf',
           'write_txt', 'write_pbm', 'write_pam', 'write_ppm', 'write_xpm',
           'write_xbm', 'write_tex', 'write_terminal')

CREATOR = 'Segno <https://pypi.org/project/segno/>'


@contextmanager
def writable(file_or_path, mode, encoding=None):
    pass


def colorful(dark, light):
    """\
    Decorator to inject a module type -> color mapping into the decorated function.
    """
    def decorate(f):
        pass
    return decorate


def _valid_width_height_and_border(matrix_size, scale, border):
    pass


@colorful(dark='#000', light=None)
def write_svg(matrix, matrix_size, out, colormap, scale=1, border=None, xmldecl=True,
              svgns=True, title=None, desc=None, svgid=None, svgclass='segno',
              lineclass='qrline', omitsize=False, unit=None, encoding='utf-8',
              svgversion=None, nl=True, draw_transparent=False):
    pass


_replace_quotes = partial(re.compile(br'(=)"([^"]+)"').sub, br"\1'\2'")


def as_svg_data_uri(matrix, matrix_size, scale=1, border=None,
                    xmldecl=False, svgns=True, title=None,
                    desc=None, svgid=None, svgclass='segno',
                    lineclass='qrline', omitsize=False, unit='',
                    encoding='utf-8', svgversion=None, nl=False,
                    encode_minimal=False, omit_charset=False, **kw):
    pass


def write_svg_debug(matrix, matrix_size, out, scale=15, border=None,
                    fallback_color='fuchsia', colormap=None,
                    add_legend=True):  # pragma: no cover
    pass


def write_eps(matrix, matrix_size, out, scale=1, border=None, dark='#000', light=None):
    pass


def as_png_data_uri(matrix, matrix_size, scale=1, border=None, compresslevel=9, **kw):
    pass


@colorful(dark='#000', light='#fff')
def write_png(matrix, matrix_size, out, colormap, scale=1, border=None, compresslevel=9, dpi=None):
    pass


def write_pdf(matrix, matrix_size, out, scale=1, border=None, dark='#000',
              light=None, compresslevel=9):
    pass


def write_txt(matrix, matrix_size, out, border=None, dark='1', light='0'):
    pass


def write_pbm(matrix, matrix_size, out, scale=1, border=None, plain=False):
    pass


def write_pam(matrix, matrix_size, out, scale=1, border=None, dark='#000', light='#fff'):
    pass


@colorful(dark='#000', light='#fff')
def write_ppm(matrix, matrix_size, out, colormap, scale=1, border=None):
    pass


def write_xpm(matrix, matrix_size, out, scale=1, border=None, dark='#000',
              light='#fff', name='img'):
    pass


def write_xbm(matrix, matrix_size, out, scale=1, border=None, name='img'):
    pass


def write_tex(matrix, matrix_size, out, scale=1, border=None, dark='black', unit='pt', url=None):
    pass


def write_terminal(matrix, matrix_size, out, border=None):
    pass


def write_terminal_win(matrix, matrix_size, border=None):  # pragma: no cover
    pass


def write_terminal_compact(matrix, matrix_size, out, border=None):
    pass


def _color_to_rgb_or_rgba(color, alpha_float=True):
    pass


def _color_to_webcolor(color, allow_css3_colors=True, optimize=True):
    pass


def color_to_rgb_hex(color):
    pass


def _color_is_black(color):
    pass


def _color_is_white(color):
    pass


def _color_to_rgb(color):
    pass


def _color_to_rgba(color, alpha_float=True):
    pass


def _hex_to_rgb_or_rgba(color, alpha_float=True):
    pass


_ALPHA_COMMONS = {255: 1.0, 128: .5, 64: .25, 32: .125, 16: .625, 0: 0.0}


def _alpha_value(color, alpha_float):
    pass


def _invert_color(rgb_or_rgba):
    pass


_NAME2RGB = {
    'aliceblue': (240, 248, 255),
    'antiquewhite': (250, 235, 215),
    'aqua': (0, 255, 255),
    'aquamarine': (127, 255, 212),
    'azure': (240, 255, 255),
    'beige': (245, 245, 220),
    'bisque': (255, 228, 196),
    'black': (0, 0, 0),
    'blanchedalmond': (255, 235, 205),
    'blue': (0, 0, 255),
    'blueviolet': (138, 43, 226),
    'brown': (165, 42, 42),
    'burlywood': (222, 184, 135),
    'cadetblue': (95, 158, 160),
    'chartreuse': (127, 255, 0),
    'chocolate': (210, 105, 30),
    'coral': (255, 127, 80),
    'cornflowerblue': (100, 149, 237),
    'cornsilk': (255, 248, 220),
    'crimson': (220, 20, 60),
    'cyan': (0, 255, 255),
    'darkblue': (0, 0, 139),
    'darkcyan': (0, 139, 139),
    'darkgoldenrod': (184, 134, 11),
    'darkgray': (169, 169, 169),
    'darkgreen': (0, 100, 0),
    'darkgrey': (169, 169, 169),
    'darkkhaki': (189, 183, 107),
    'darkmagenta': (139, 0, 139),
    'darkolivegreen': (85, 107, 47),
    'darkorange': (255, 140, 0),
    'darkorchid': (153, 50, 204),
    'darkred': (139, 0, 0),
    'darksalmon': (233, 150, 122),
    'darkseagreen': (143, 188, 143),
    'darkslateblue': (72, 61, 139),
    'darkslategray': (47, 79, 79),
    'darkslategrey': (47, 79, 79),
    'darkturquoise': (0, 206, 209),
    'darkviolet': (148, 0, 211),
    'deeppink': (255, 20, 147),
    'deepskyblue': (0, 191, 255),
    'dimgray': (105, 105, 105),
    'dimgrey': (105, 105, 105),
    'dodgerblue': (30, 144, 255),
    'firebrick': (178, 34, 34),
    'floralwhite': (255, 250, 240),
    'forestgreen': (34, 139, 34),
    'fuchsia': (255, 0, 255),
    'gainsboro': (220, 220, 220),
    'ghostwhite': (248, 248, 255),
    'gold': (255, 215, 0),
    'goldenrod': (218, 165, 32),
    'gray': (128, 128, 128),
    'green': (0, 128, 0),
    'greenyellow': (173, 255, 47),
    'grey': (128, 128, 128),
    'honeydew': (240, 255, 240),
    'hotpink': (255, 105, 180),
    'indianred': (205, 92, 92),
    'indigo': (75, 0, 130),
    'ivory': (255, 255, 240),
    'khaki': (240, 230, 140),
    'lavender': (230, 230, 250),
    'lavenderblush': (255, 240, 245),
    'lawngreen': (124, 252, 0),
    'lemonchiffon': (255, 250, 205),
    'lightblue': (173, 216, 230),
    'lightcoral': (240, 128, 128),
    'lightcyan': (224, 255, 255),
    'lightgoldenrodyellow': (250, 250, 210),
    'lightgray': (211, 211, 211),
    'lightgreen': (144, 238, 144),
    'lightgrey': (211, 211, 211),
    'lightpink': (255, 182, 193),
    'lightsalmon': (255, 160, 122),
    'lightseagreen': (32, 178, 170),
    'lightskyblue': (135, 206, 250),
    'lightslategray': (119, 136, 153),
    'lightslategrey': (119, 136, 153),
    'lightsteelblue': (176, 196, 222),
    'lightyellow': (255, 255, 224),
    'lime': (0, 255, 0),
    'limegreen': (50, 205, 50),
    'linen': (250, 240, 230),
    'magenta': (255, 0, 255),
    'maroon': (128, 0, 0),
    'mediumaquamarine': (102, 205, 170),
    'mediumblue': (0, 0, 205),
    'mediumorchid': (186, 85, 211),
    'mediumpurple': (147, 112, 219),
    'mediumseagreen': (60, 179, 113),
    'mediumslateblue': (123, 104, 238),
    'mediumspringgreen': (0, 250, 154),
    'mediumturquoise': (72, 209, 204),
    'mediumvioletred': (199, 21, 133),
    'midnightblue': (25, 25, 112),
    'mintcream': (245, 255, 250),
    'mistyrose': (255, 228, 225),
    'moccasin': (255, 228, 181),
    'navajowhite': (255, 222, 173),
    'navy': (0, 0, 128),
    'oldlace': (253, 245, 230),
    'olive': (128, 128, 0),
    'olivedrab': (107, 142, 35),
    'orange': (255, 165, 0),
    'orangered': (255, 69, 0),
    'orchid': (218, 112, 214),
    'palegoldenrod': (238, 232, 170),
    'palegreen': (152, 251, 152),
    'paleturquoise': (175, 238, 238),
    'palevioletred': (219, 112, 147),
    'papayawhip': (255, 239, 213),
    'peachpuff': (255, 218, 185),
    'peru': (205, 133, 63),
    'pink': (255, 192, 203),
    'plum': (221, 160, 221),
    'powderblue': (176, 224, 230),
    'purple': (128, 0, 128),
    'red': (255, 0, 0),
    'rosybrown': (188, 143, 143),
    'royalblue': (65, 105, 225),
    'saddlebrown': (139, 69, 19),
    'salmon': (250, 128, 114),
    'sandybrown': (244, 164, 96),
    'seagreen': (46, 139, 87),
    'seashell': (255, 245, 238),
    'sienna': (160, 82, 45),
    'silver': (192, 192, 192),
    'skyblue': (135, 206, 235),
    'slateblue': (106, 90, 205),
    'slategray': (112, 128, 144),
    'slategrey': (112, 128, 144),
    'snow': (255, 250, 250),
    'springgreen': (0, 255, 127),
    'steelblue': (70, 130, 180),
    'tan': (210, 180, 140),
    'teal': (0, 128, 128),
    'thistle': (216, 191, 216),
    'tomato': (255, 99, 71),
    'turquoise': (64, 224, 208),
    'violet': (238, 130, 238),
    'wheat': (245, 222, 179),
    'white': (255, 255, 255),
    'whitesmoke': (245, 245, 245),
    'yellow': (255, 255, 0),
    'yellowgreen': (154, 205, 50),
}


def _make_colormap(matrix_width, matrix_height, dark, light,
                   finder_dark=False, finder_light=False,
                   data_dark=False, data_light=False,
                   version_dark=False, version_light=False,
                   format_dark=False, format_light=False,
                   alignment_dark=False, alignment_light=False,
                   timing_dark=False, timing_light=False,
                   separator=False, dark_module=False,
                   quiet_zone=False):
    """\
    Creates and returns a module type -> color map.

    The result can be used for serializers which support more than two colors.

    Examples

    .. code-block:: python

        # All dark modules (data, version, ...) will be dark red, the dark
        # modules of the finder patterns will be blue
        # The light modules will be rendered in the serializer's default color
        # (usually white)
        cm = colormap(dark='darkred', finder_dark='blue')

        # Use the serializer's default colors for dark / light modules
        # (usually black and white) but the dark modules of the timing patterns
        # will be brown
        cm = colormap(timing_dark=(165, 42, 42))

    :param int matrix_width: Matrix width
    :param int matrix_height: Matrix height
    :param dark: Default color of dark modules
    :param light: Default color of light modules
    :param finder_dark: Color of the dark modules of the finder patterns.
    :param finder_light: Color of the light modules of the finder patterns.
    :param data_dark: Color of the dark data modules.
    :param data_light: Color of the light data modules.
    :param version_dark: Color of the dark modules of the version information.
    :param version_light: Color of the light modules of the version information.
    :param format_dark: Color of the dark modules of the format information.
    :param format_light: Color of the light modules of the format information.
    :param alignment_dark: Color of the dark modules of the alignment patterns.
    :param alignment_light: Color of the light modules of the alignment patterns.
    :param timing_dark: Color of the dark modules of the timing patterns.
    :param timing_light: Color of the light modules of the timing patterns.
    :param separator: Color of the separator.
    :param dark_module: Color of the dark module.
    :param quiet_zone: Color of the quiet zone / border.
    :rtype: dict
    """
    unsupported = ()
    is_square = matrix_width == matrix_height
    if not is_square:  # rMQR
        unsupported = [consts.TYPE_DARKMODULE, consts.TYPE_VERSION_DARK, consts.TYPE_VERSION_LIGHT]
        if matrix_width < 43:  # rMQR R11x27, R13x27, …
            unsupported.extend((consts.TYPE_ALIGNMENT_PATTERN_DARK, consts.TYPE_ALIGNMENT_PATTERN_LIGHT))
    elif matrix_width < 45:  # QR Code version 7
        unsupported = [consts.TYPE_VERSION_DARK, consts.TYPE_VERSION_LIGHT]
        if matrix_width < 21:  # Lesser than QR Code version 1 => Micro QR code
            unsupported.extend([consts.TYPE_DARKMODULE,
                                consts.TYPE_ALIGNMENT_PATTERN_DARK,
                                consts.TYPE_ALIGNMENT_PATTERN_LIGHT])
    mt2color = {
        consts.TYPE_FINDER_PATTERN_DARK: finder_dark if finder_dark is not False else dark,
        consts.TYPE_FINDER_PATTERN_LIGHT: finder_light if finder_light is not False else light,
        consts.TYPE_DATA_DARK: data_dark if data_dark is not False else dark,
        consts.TYPE_DATA_LIGHT: data_light if data_light is not False else light,
        consts.TYPE_VERSION_DARK: version_dark if version_dark is not False else dark,
        consts.TYPE_VERSION_LIGHT: version_light if version_light is not False else light,
        consts.TYPE_ALIGNMENT_PATTERN_DARK: alignment_dark if alignment_dark is not False else dark,
        consts.TYPE_ALIGNMENT_PATTERN_LIGHT: alignment_light if alignment_light is not False else light,
        consts.TYPE_TIMING_DARK: timing_dark if timing_dark is not False else dark,
        consts.TYPE_TIMING_LIGHT: timing_light if timing_light is not False else light,
        consts.TYPE_FORMAT_DARK: format_dark if format_dark is not False else dark,
        consts.TYPE_FORMAT_LIGHT: format_light if format_light is not False else light,
        consts.TYPE_SEPARATOR: separator if separator is not False else light,
        consts.TYPE_DARKMODULE: dark_module if dark_module is not False else dark,
        consts.TYPE_QUIET_ZONE: quiet_zone if quiet_zone is not False else light,
    }
    return {mt: val for mt, val in mt2color.items() if mt not in unsupported}


_VALID_SERIALIZERS = {
    'svg': write_svg,
    'png': write_png,
    'eps': write_eps,
    'txt': write_txt,
    'pdf': write_pdf,
    'ans': write_terminal,
    'pbm': write_pbm,
    'pam': write_pam,
    'ppm': write_ppm,
    'tex': write_tex,
    'xbm': write_xbm,
    'xpm': write_xpm,
}


def save(matrix, matrix_size, out, kind=None, **kw):
    pass
