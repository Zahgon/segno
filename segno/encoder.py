from operator import itemgetter, gt, lt, xor
from functools import partial, reduce
from itertools import islice, chain, product
import re
import math
import codecs
from collections import namedtuple
from . import consts
from itertools import zip_longest
import sys
_MAX_PENALTY_SCORE = sys.maxsize
del sys

__all__ = ('encode', 'encode_sequence', 'DataOverflowError')


class DataOverflowError(ValueError):
    pass


Code = namedtuple('Code', 'matrix version error mask segments')


def encode(content, error=None, version=None, mode=None, mask=None,
           encoding=None, eci=False, micro=None, boost_error=True):
    """\
    Creates a (Micro) QR code.

    See :py:func:`segno.make` for a detailed description of the parameters.

    Contrary to ``make`` this function returns a named tuple:
    ``(matrix, version, error, mask, segments)``

    Note that ``version`` is always an integer referring
    to the values of the :py:mod:`segno.consts` constants. ``error`` is ``None``
    iff a M1 QR Code was generated, otherwise it is always an integer.

    :rtype: namedtuple
    """
    version = normalize_version(version)
    if not micro and micro is not None and version in consts.MICRO_VERSIONS:
        raise ValueError(f'A Micro QR Code version ("{get_version_name(version)}") '
                         'is provided but parameter "micro" is False')
    if micro and version is not None and version not in consts.MICRO_VERSIONS:
        raise ValueError(f'Illegal Micro QR Code version "{get_version_name(version)}"')
    error = normalize_errorlevel(error, accept_none=True)
    mode = normalize_mode(mode)
    if mode is not None and version is not None \
            and not is_mode_supported(mode, version):
        raise ValueError(f'Mode "{get_mode_name(mode)}" is not available in version "{get_version_name(version)}"')
    if error == consts.ERROR_LEVEL_H and (micro or version in consts.MICRO_VERSIONS):
        raise ValueError('Error correction level "H" is not available for Micro QR Codes')
    if eci and (micro or version in consts.MICRO_VERSIONS):
        raise ValueError('The ECI mode is not available for Micro QR Codes')
    segments = prepare_data(content, mode, encoding)
    guessed_version = find_version(segments, error, eci=eci, micro=micro)
    if version is None:
        version = guessed_version
    elif guessed_version > version:
        raise DataOverflowError(f'The provided data does not fit into version "{get_version_name(version)}"'
                                f'Proposal: version {get_version_name(guessed_version)}')
    if error is None and version != consts.VERSION_M1:
        error = consts.ERROR_LEVEL_L
    is_micro = version < 1
    mask = normalize_mask(mask, is_micro)
    return _encode(segments, error, version, mask, eci, boost_error)


def encode_sequence(content, error=None, version=None, mode=None, mask=None,
                    encoding=None, eci=False, boost_error=True, symbol_count=None):
    pass


def _encode(segments, error, version, mask, eci, boost_error, sa_info=None):
    """\
    Creates a (Micro) QR code.

    NOTE: This function does not check if the input is valid and does not belong
    to the public API.
    """
    is_micro = version < 1
    sa_mode = sa_info is not None
    buff = Buffer()
    ver = version
    ver_range = version
    if not is_micro:
        ver = None
        ver_range = version_range(version)
    if boost_error:
        error = boost_error_level(version, error, segments, eci, is_sa=sa_mode)
    if sa_mode:
        for i in sa_info[:3]:
            buff.append_bits(i, 4)
        buff.append_bits(sa_info.parity, 8)
    for segment in segments:
        write_segment(buff, segment, ver, ver_range, eci)
    capacity = consts.SYMBOL_CAPACITY[version][error]
    write_terminator(buff, capacity, ver, len(buff))
    write_padding_bits(buff, version, len(buff))
    write_pad_codewords(buff, version, capacity, len(buff))
    buff = make_final_message(version, error, buff)
    width = calc_matrix_size(version)
    height = width
    matrix = make_matrix(width, height)
    add_finder_patterns(matrix, width, height)
    add_alignment_patterns(matrix, width, height)
    add_codewords(matrix, buff, version)
    mask, matrix = find_and_apply_best_mask(matrix, width, height, mask)
    add_format_info(matrix, version, error, mask)
    add_version_info(matrix, version)
    return Code(matrix, version, error, mask, segments)


def boost_error_level(version, error, segments, eci, is_sa=False):
    """\
    Increases the error correction level if possible.

    Returns either the provided or a better error correction level which works
    while keeping the (Micro) QR Code version.

    :param int version: Version constant.
    :param int|None error: Error level constant or ``None``
    :param Segments segments: Instance of :py:class:`Segments`
    :param bool eci: Indicates if ECI designator should be written.
    :param bool is_sa: Indicates if Structured Append mode is used.
    """
    if error not in (consts.ERROR_LEVEL_H, None) and len(segments) == 1:
        levels = [consts.ERROR_LEVEL_L, consts.ERROR_LEVEL_M,
                  consts.ERROR_LEVEL_Q, consts.ERROR_LEVEL_H]
        if version < 1:
            levels.pop()  # H isn't support by Micro QR Codes
            if version < consts.VERSION_M4:
                levels.pop()  # Error level Q isn't supported by M2 and M3
        data_length = segments.bit_length_with_overhead(version, eci, is_sa=is_sa)
        for error_level in levels[levels.index(error) + 1:]:
            if consts.SYMBOL_CAPACITY[version][error_level] >= data_length:
                error = error_level
            else:
                break
    return error


def write_segment(buff, segment, ver, ver_range, eci=False):
    """\
    Writes a segment.

    :param buff: The byte buffer.
    :param _Segment segment: The segment to serialize.
    :param ver: ``None`` if a QR Code is written, "M1", "M2", "M3", or "M4" if a
            Micro QR Code is written.
    :param ver_range: "M1", "M2", "M3", or "M4" if a Micro QR Code is written,
            otherwise a constant representing a range of QR Code versions.
    """
    mode = segment.mode
    append_bits = buff.append_bits
    if eci and mode == consts.MODE_BYTE \
            and segment.encoding != consts.DEFAULT_BYTE_ENCODING:
        append_bits(consts.MODE_ECI, 4)
        append_bits(get_eci_assignment_number(segment.encoding), 8)
    if ver is None:  # QR Code
        append_bits(mode, 4)
        if mode == consts.MODE_HANZI:
            subset = 1  # Indicator for GB2312 subset
            append_bits(subset, 4)
    elif ver > consts.VERSION_M1:  # Micro QR Code (M1 has no mode indicator)
        append_bits(consts.MODE_TO_MICRO_MODE_MAPPING[mode], ver + 3)
    append_bits(segment.char_count,
                consts.CHAR_COUNT_INDICATOR_LENGTH[mode][ver_range])
    buff.extend(segment.bits)


def write_terminator(buff, capacity, ver, length):
    """\
    Writes the terminator.

    :param buff: The byte buffer.
    :param capacity: Symbol capacity.
    :param ver: ``None`` if a QR Code is written, "M1", "M2", "M3", or "M4" if a
            Micro QR Code is written.
    :param length: Length of the data bit stream.
    """
    buff.extend([0] * min(capacity - length, consts.TERMINATOR_LENGTH[ver]))


def write_padding_bits(buff, version, length):
    """\
    Writes padding bits if the data stream does not meet the codeword boundary.

    :param buff: The byte buffer.
    :param int length: Data stream length.
    """
    if version not in (consts.VERSION_M1, consts.VERSION_M3):
        buff.extend([0] * (8 - (length % 8)))


def write_pad_codewords(buff, version, capacity, length):
    """\
    Writes the pad codewords iff the data does not fill the capacity of the
    symbol.

    :param buff: The byte buffer.
    :param int version: The (Micro) QR Code version.
    :param int capacity: The total capacity of the symbol (incl. error correction)
    :param int length: Length of the data bit stream.
    """
    write = buff.extend
    if version in (consts.VERSION_M1, consts.VERSION_M3):
        write([0] * (capacity - length))
    else:
        pad_codewords = ((1, 1, 1, 0, 1, 1, 0, 0), (0, 0, 0, 1, 0, 0, 0, 1))
        for i in range(capacity // 8 - length // 8):
            write(pad_codewords[i % 2])


_FINDER_PATTERN = ((0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0),
                   (0x0, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x0),
                   (0x0, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1, 0x0),
                   (0x0, 0x1, 0x0, 0x1, 0x1, 0x1, 0x0, 0x1, 0x0),
                   (0x0, 0x1, 0x0, 0x1, 0x1, 0x1, 0x0, 0x1, 0x0),
                   (0x0, 0x1, 0x0, 0x1, 0x1, 0x1, 0x0, 0x1, 0x0),
                   (0x0, 0x1, 0x0, 0x0, 0x0, 0x0, 0x0, 0x1, 0x0),
                   (0x0, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x1, 0x0),
                   (0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0))


def add_finder_patterns(matrix, width, height):
    """\
    Adds the finder pattern(s) with the separators to the matrix.

    QR Codes get three finder patterns, Micro QR Codes have just one finder
    pattern.

    ISO/IEC 18004:2015(E) -- 6.3.3 Finder pattern (page 16)
    ISO/IEC 18004:2015(E) -- 6.3.4 Separator (page 17)

    :param matrix: The matrix.
    :param tuple(int, int) matrix_size: Tuple of width and height of the matrix.
    """
    is_square = width == height
    corners = ((0, 0), (0, len(matrix) - 8), (-8, 0))  # Upper left, upper right, bottom left
    if is_square and width < 21:
        corners = ((0, 0),)
    finder_range = range(8)
    for i, j in corners:
        offset = 1 if i == 0 else 0
        sepoffset = 0 if j != 0 else 1
        for r in finder_range:
            matrix[i + r][j:j + 8] = _FINDER_PATTERN[offset + r][sepoffset:sepoffset + 8]


def add_timing_pattern(matrix, is_micro):
    """\
    Adds the (horizontal and vertical) timinig pattern to the provided `matrix`.

    ISO/IEC 18004:2015(E) -- 6.3.5 Timing pattern (page 17)

    :param matrix: Matrix to add the timing pattern into.
    :param bool is_micro: Indicates if the timing pattern for a Micro QR Code
        should be added.
    """
    j, stop = (0, len(matrix)) if is_micro else (6, len(matrix) - 8)
    col = matrix[j]
    bit = 0x1
    for i in range(8, stop):
        matrix[i][j] = bit
        col[i] = bit
        bit ^= 0x1


def add_alignment_patterns(matrix, width, height):
    """\
    Adds the adjustment patterns to the matrix. For versions < 2 this is a
    no-op.

    ISO/IEC 18004:2015(E) -- 6.3.6 Alignment patterns (page 17)
    ISO/IEC 18004:2015(E) -- Annex E Position of alignment patterns (page 83)

    :param matrix: An iterable of bytearrays.
    :param tuple(int, int) matrix_size: Tuple of width and height of the matrix.
    """
    is_square = width == height
    version = (width - 17) // 4  # QR Codes: version * 4 +  17 == width / height of the matrix w/o border
    if is_square and version < 2:  # QR Codes version < 2 don't have alignment patterns
        return
    pattern = (0x1, 0x1, 0x1, 0x1, 0x1,
               0x1, 0x0, 0x0, 0x0, 0x1,
               0x1, 0x0, 0x1, 0x0, 0x1,
               0x1, 0x0, 0x0, 0x0, 0x1,
               0x1, 0x1, 0x1, 0x1, 0x1)
    positions = consts.ALIGNMENT_POS[version - 2]
    alignment_range = range(5)
    min_pos = positions[0]
    max_pos = positions[-1]
    finder_positions = ((min_pos, min_pos), (min_pos, max_pos), (max_pos, min_pos))
    for x, y in product(positions, repeat=2):
        if (x, y) in finder_positions:
            continue
        i, j = x - 2, y - 2
        for r in alignment_range:
            matrix[i + r][j:j + 5] = pattern[r * 5:r * 5 + 5]


def add_codewords(matrix, codewords, version):
    """\
    Adds the codewords (data and error correction) to the provided matrix.

    ISO/IEC 18004:2015(E) -- 7.7.3 Symbol character placement (page 46)

    :param matrix: The matrix to add the codewords into.
    :param codewords: Sequence of bits
    :param int version: The (Micro) QR Code version constant.
    """
    matrix_size = len(matrix)
    is_micro = version < 1
    inc = 0 if version not in (consts.VERSION_M1, consts.VERSION_M3) else 2
    idx = 0  # Pointer to the current codeword
    codeword_length = len(codewords)
    range_two = range(2)
    for right in range(matrix_size - 1, 0, -2):
        if not is_micro and right <= 6:
            right -= 1
        for vertical in range(matrix_size):
            for z in range_two:
                j = right - z
                upwards = ((right + inc) & 2) == 0
                if not is_micro:
                    upwards ^= j < 6
                i = (matrix_size - 1 - vertical) if upwards else vertical
                row = matrix[i]
                if row[j] == 0x2 and idx < codeword_length:
                    row[j] = codewords[idx]
                    idx += 1
    if idx != len(codewords):  # pragma: no cover
        raise ValueError('Internal error: Adding codewords to matrix failed. '
                         f'Added {idx} of {len(codewords)} codewords')


def make_final_message(version, error, buff):
    """\
    Constructs the final message (codewords incl. error correction).

    ISO/IEC 18004:2015(E) -- 7.6 Constructing the final message codeword sequence (page 45)

    :param int version: (Micro) QR Code version constant.
    :param int error: Error level constant.
    :param buff: Byte buffer.
    :return: Byte buffer representing the final message.
    """
    def to_binary(val, length=8):
        return ((val >> i) & 1 for i in reversed(range(length)))

    ec_infos = consts.ECC[version][error]
    data_blocks, error_blocks = make_blocks(ec_infos, buff)
    cw_four = None
    if version in (consts.VERSION_M1, consts.VERSION_M3):
        cw_four = to_binary(data_blocks[0].pop(-1) >> 4, 4)
    res = Buffer()
    res.extend(chain(*map(to_binary, (x for x in chain.from_iterable(zip_longest(*data_blocks)) if x is not None))))
    if cw_four is not None:
        res.extend(cw_four)
    res.extend(chain(*map(to_binary, (x for x in chain.from_iterable(zip_longest(*error_blocks)) if x is not None))))
    # modules in the encoding region
    remainder = 0
    if version in (2, 3, 4, 5, 6):
        remainder = 7
    elif version in (14, 15, 16, 17, 18, 19, 20, 28, 29, 30, 31, 32, 33, 34):
        remainder = 3
    elif version in (21, 22, 23, 24, 25, 26, 27):
        remainder = 4
    res.extend(b'\0' * remainder)
    return res


def make_blocks(ec_infos, buff):
    """\
    Returns the data and error blocks.

    :param ec_infos: Iterable of ECC information
    :param buff: Byte buffer.
    """
    codewords = buff.toints()
    data_blocks, error_blocks = [], []
    append_data_block = data_blocks.append
    append_error_block = error_blocks.append
    gen_log = consts.GALIOS_LOG
    gen_exp = consts.GALIOS_EXP
    for ec_info in ec_infos:
        num_error_words = ec_info.num_total - ec_info.num_data
        gen = consts.GEN_POLY[num_error_words]
        range_error_words = range(num_error_words)
        for i in range(ec_info.num_blocks):
            block = bytearray(islice(codewords, ec_info.num_data))
            append_data_block(block)
            len_data = len(block)
            error_block = bytearray(block)
            error_block.extend([0] * num_error_words)
            for k in range(len_data):
                coef = error_block[k]
                if coef != 0:  # log(0) is undefined
                    lcoef = gen_log[coef]
                    for n in range_error_words:
                        error_block[k + n + 1] ^= gen_exp[lcoef + gen[n]]
            append_error_block(error_block[len_data:])
    return data_blocks, error_blocks


def find_and_apply_best_mask(matrix, width, height, proposed_mask=None):
    """\
    Applies all mask patterns against the provided QR Code matrix and returns
    the best matrix and best pattern.

    ISO/IEC 18004:2015(E) -- 7.8.2 Data mask patterns (page 50)
    ISO/IEC 18004:2015(E) -- 7.8.3 Evaluation of data masking results (page 53)
    ISO/IEC 18004:2015(E) -- 7.8.3.1 Evaluation of QR Code symbols (page 53/54)
    ISO/IEC 18004:2015(E) -- 7.8.3.2 Evaluation of Micro QR Code symbols (page 54/55)

    :param matrix: A matrix.
    :param tuple(int, int) matrix_size: Tuple of width and height of the matrix.
    :param proposed_mask: Optional int to indicate the preferred mask.
    :rtype: tuple
    :return: A tuple of the best matrix and best data mask pattern index.
    """
    is_better = lt
    best_score = _MAX_PENALTY_SCORE
    eval_mask = evaluate_mask
    is_micro = width == height and width < 21
    if is_micro:
        is_better = gt
        best_score = -1
        eval_mask = evaluate_micro_mask
    function_matrix = make_matrix(width, height)
    add_finder_patterns(function_matrix, width, height)
    add_alignment_patterns(function_matrix, width, height)
    if not is_micro:
        function_matrix[-8][8] = 0x1

    def is_encoding_region(i, j):
        return function_matrix[i][j] > 0x1

    mask_patterns = get_data_mask_functions(is_micro)
    if proposed_mask is not None:
        apply_mask(matrix, mask_patterns[proposed_mask], width, height,
                   is_encoding_region)
        return proposed_mask, matrix

    best_matrix = None
    for mask_number, mask_pattern in enumerate(mask_patterns):
        m = [ba[:] for ba in matrix]
        apply_mask(m, mask_pattern, width, height, is_encoding_region)
        score = eval_mask(m, width, height)
        if is_better(score, best_score):
            best_score = score
            best_pattern = mask_number
            best_matrix = tuple(m)
    return best_pattern, best_matrix


def apply_mask(matrix, mask_pattern, width, height, is_encoding_region):
    """\
    Applies the provided mask pattern on the `matrix`.

    ISO/IEC 18004:2015(E) -- 7.8.2 Data mask patterns (page 50)

    :param tuple matrix: A tuple of bytearrays
    :param mask_pattern: A mask pattern (a function)
    :param int matrix_size: width or height of the matrix
    :param is_encoding_region: A function which returns ``True`` iff the
            row index / col index belongs to the data region.
    """
    width_range = range(width)
    for i in range(height):
        row = matrix[i]
        for j in width_range:
            if is_encoding_region(i, j):
                row[j] ^= mask_pattern(i, j)


def evaluate_mask(matrix, width, height):
    pass


def mask_scores(matrix, width, height):
    pass


def evaluate_micro_mask(matrix, width, height):
    pass


def calc_format_info(version, error, mask_pattern):
    """\
    Returns the format information for the provided error level and mask patttern.

    ISO/IEC 18004:2015(E) -- 7.9 Format information (page 55)
    ISO/IEC 18004:2015(E) -- Table C.1 — Valid format information bit sequences (page 80)

    :param int version: Version constant
    :param int error: Error level constant.
    :param int mask_pattern: Mask pattern number.
    """
    fmt = mask_pattern
    if version > 0:
        if error == consts.ERROR_LEVEL_L:
            fmt += 0x08
        elif error == consts.ERROR_LEVEL_H:
            fmt += 0x10
        elif error == consts.ERROR_LEVEL_Q:
            fmt += 0x18
        format_info = consts.FORMAT_INFO[fmt]
    else:
        fmt += consts.ERROR_LEVEL_TO_MICRO_MAPPING[version][error] << 2
        format_info = consts.FORMAT_INFO_MICRO[fmt]
    return format_info


def add_format_info(matrix, version, error, mask_pattern):
    """\
    Adds the format information into the provided matrix.

    ISO/IEC 18004:2015(E) -- 7.9 Format information (page 55)
    ISO/IEC 18004:2015(E) -- 7.9.1 QR Code symbols
    ISO/IEC 18004:2015(E) -- 7.9.2 Micro QR Code symbols

    :param matrix: The matrix.
    :param int version: Version constant
    :param int error: Error level constant.
    :param int mask_pattern: Mask pattern number.
    """
    is_micro = version < 1
    format_info = calc_format_info(version, error, mask_pattern)
    voffset = int(is_micro)
    hoffset = voffset
    row_eight = matrix[8]
    for i in range(8):
        vbit = (format_info >> i) & 0x01
        hbit = (format_info >> (14 - i)) & 0x01
        if i == 6 and not is_micro:  # Timing pattern
            voffset += 1
            hoffset = 1
        matrix[i + voffset][8] = vbit
        row_eight[i + hoffset] = hbit
        if not is_micro:
            row_eight[-1 - i] = vbit
            matrix[-1 - i][8] = hbit
    if not is_micro:
        matrix[-8][8] = 0x1


def add_version_info(matrix, version):
    """\
    Adds the version information to the matrix, for versions < 7 this is a no-op.

    ISO/IEC 18004:2015(E) -- 7.10 Version information (page 58)
    """
    if version < 7:
        return
    version_info = consts.VERSION_INFO[version - 7]
    for i in range(6):
        bit1 = (version_info >> (i * 3)) & 0x01
        bit2 = (version_info >> ((i * 3) + 1)) & 0x01
        bit3 = (version_info >> ((i * 3) + 2)) & 0x01
        matrix[-11][i] = bit1
        matrix[-10][i] = bit2
        matrix[-9][i] = bit3
        row = matrix[i]
        row[-11] = bit1
        row[-10] = bit2
        row[-9] = bit3


def prepare_data(content, mode, encoding):
    """\
    Returns an iterable of `Segment` instances.

    If `content` is a string, an integer, or bytes, the returned tuple will
    have a single item. If `content` is a list or a tuple, a tuple of
    `Segment` instances of the same length is returned.

    :param content: Either a string, bytes, an integer or an iterable.
    :type content: str, bytes, int, tuple, list or any iterable
    :param mode: The global mode. If `content` is list/tuple, the `Segment`
            instances may have a different mode.
    :param encoding: The global encoding. If `content` is a list or a tuple,
            the `Segment` instances may have a different encoding.
    :rtype: Segments
    """
    segments = Segments()
    add_segment = segments.add_segment
    if isinstance(content, (str, bytes, int)):
        add_segment(make_segment(content, mode, encoding))
        return segments
    for item in content:
        seg_content, seg_mode, seg_encoding = item, mode, encoding
        if isinstance(item, tuple):
            seg_content = item[0]
            if len(item) > 1:
                seg_mode = item[1] or mode  # item[1] could be None
            if len(item) > 2:
                seg_encoding = item[2] or encoding  # item[2] may be None
        add_segment(make_segment(seg_content, seg_mode, seg_encoding))
    return segments


def data_to_bytes(data, encoding):
    """\
    Converts the provided data into bytes. If the data is already a byte
    sequence, it will be left unchanged.

    This function tries to use the provided `encoding` (if not ``None``)
    or the default encoding (ISO/IEC 8859-1). It uses UTF-8 as fallback.

    Returns the (byte) data, the length of the data and the encoding of the data.

    :param data: The data to encode
    :type data: str or bytes
    :param encoding: str or ``None``
    :rtype: tuple: data, data length, encoding
    """
    if isinstance(data, bytes):
        return data, len(data), encoding or consts.DEFAULT_BYTE_ENCODING
    data = str(data)
    if encoding is not None:
        # Use the provided encoding; could raise an exception by intention
        data = data.encode(encoding)
    else:
        try:
            encoding = consts.DEFAULT_BYTE_ENCODING
            data = data.encode(encoding)
        except UnicodeError:
            try:
                encoding = consts.KANJI_ENCODING
                data = data.encode(encoding)
            except UnicodeError:
                encoding = 'utf-8'
                data = data.encode(encoding)
    return data, len(data), encoding


def make_segment(data, mode, encoding=None):
    """\
    Creates a :py:class:`Segment`.

    :param data: The segment data
    :param mode: The mode.
    :param encoding: The encoding.
    :rtype: _Segment
    """
    if mode == consts.MODE_HANZI:
        encoding = consts.HANZI_ENCODING
    segment_data, segment_length, segment_encoding = data_to_bytes(data, encoding)
    segment_mode = mode
    guessed_mode = find_mode(segment_data) if segment_mode != consts.MODE_BYTE else consts.MODE_BYTE
    if segment_mode is not None:
        if segment_mode < guessed_mode:
            raise ValueError(f'The provided mode "{get_mode_name(segment_mode)}" '
                             f'is not applicable for {segment_data!r}. '
                             f'Proposal: {get_mode_name(guessed_mode)}')
    else:
        segment_mode = guessed_mode
    if segment_mode != consts.MODE_BYTE:
        segment_encoding = None
    char_count = segment_length if segment_mode not in (consts.MODE_KANJI, consts.MODE_HANZI) else segment_length // 2
    buff = Buffer()
    append_bits = buff.append_bits
    if segment_mode == consts.MODE_NUMERIC:
        for i in range(0, segment_length, 3):
            chunk = segment_data[i:i + 3]
            append_bits(int(chunk), len(chunk) * 3 + 1)
    elif segment_mode == consts.MODE_ALPHANUMERIC:
        to_byte = consts.ALPHANUMERIC_CHARS.find
        for i in range(0, segment_length, 2):
            chunk = segment_data[i:i + 2]
            if len(chunk) > 1:
                append_bits(to_byte(chunk[0]) * 45 + to_byte(chunk[1]), 11)
            else:
                append_bits(to_byte(chunk), 6)
    elif segment_mode == consts.MODE_BYTE:
        for b in segment_data:
            append_bits(b, 8)
    elif segment_mode == consts.MODE_HANZI:
        for i in range(0, segment_length, 2):
            code = (segment_data[i] << 8) | segment_data[i + 1]
            if 0xa1a1 <= code <= 0xaafe:
                diff = code - 0xa1a1
            elif 0xb0a1 <= code <= 0xfafe:
                diff = code - 0xa6a1
            else:  # pragma: no cover
                raise ValueError(f'Invalid Hanzi bytes: {code}')
            append_bits(((diff >> 8) * 0x60) + (diff & 0xff), 13)
    else:
        for i in range(0, segment_length, 2):
            code = (segment_data[i] << 8) | segment_data[i + 1]
            if 0x8140 <= code <= 0x9ffc:
                diff = code - 0x8140
            elif 0xe040 <= code <= 0xebbf:
                diff = code - 0xc140
            else:  # pragma: no cover
                raise ValueError(f'Invalid Kanji bytes: {code}')
            append_bits(((diff >> 8) * 0xc0) + (diff & 0xff), 13)
    return _Segment(buff.getbits(), char_count, segment_mode, segment_encoding)


def make_matrix(width, height, reserve_regions=True, add_timing=True):
    """\
    Creates a matrix of the provided `size` (w x h) initialized with the
    (illegal) value 0x2.

    The "timing pattern" is already added to the matrix and the version
    and format areas are initialized with 0x0.

    :param int width: Matrix width
    :param int height: Matrix height.
    :rtype: tuple of bytearrays
    """
    is_square = width == height
    is_micro = is_square and width < 21
    row = [0x2] * width
    matrix = tuple(bytearray(row) for i in range(height))
    if reserve_regions:
        if is_square and width > 41:  # QR Codes < version 7 don't have a version pattern
            for i in range(6):
                row = matrix[i]
                row[-11] = 0x0
                row[-10] = 0x0
                row[-9] = 0x0
                matrix[-11][i] = 0x0
                matrix[-10][i] = 0x0
                matrix[-9][i] = 0x0
        row_eight = matrix[8]
        for i in range(9):
            matrix[i][8] = 0x0  # Upper left
            row_eight[i] = 0x0  # Upper bottom
            if not is_micro:
                matrix[-i][8] = 0x0  # Bottom left
                row_eight[-i] = 0x0  # Upper right
    if add_timing:
        add_timing_pattern(matrix, is_micro)
    return matrix


def normalize_version(version):
    """\
    Canonicalization of the provided `version`.

    If the `version` is ``None``, this function returns ``None``. Otherwise
    this function checks if `version` is an integer or a Micro QR Code version.
    In case the string represents a Micro QR Code version, an uppercased
    string identifier is returned.

    If the `version` does not represent a valid version identifier (aside of
    ``None``) a :py:exc:`ValueError` is raised.

    :param version: An integer, a string or ``None``.
    :raises: :py:exc:`ValueError`: In case the version is not ``None`` and does not
                represent a valid (Micro) QR Code version.
    :rtype: int, str or ``None``
    """
    if version is None:
        return None
    error = False
    try:
        version = int(version)
        error = version < 1
    except (ValueError, TypeError):
        try:
            version = consts.MICRO_VERSION_MAPPING[version.upper()]
        except (KeyError, AttributeError):
            error = True
    if error or (not 0 < version < 41 and version not in consts.MICRO_VERSIONS):
        raise ValueError(f'Unsupported version "{version}". '
                         f'Supported: {", ".join(sorted(consts.MICRO_VERSION_MAPPING.keys()))} and 1 .. 40')
    return version


def normalize_mode(mode):
    """\
    Returns a (Micro) QR Code mode constant which is equivalent to the
    provided `mode`.

    In case the provided `mode` is ``None``, this function returns ``None``.
    Otherwise a mode constant is returned unless the provided parameter cannot
    be mapped to a valid mode. In the latter case, a :py:exc:`ValueError` is raised.

    :param mode: An integer or string or ``None``.
    :raises: :py:exc:`ValueError` In case the provided `mode` does not represent a valid
             QR Code mode.
    :rtype: int or None
    """
    if mode is None or mode in consts.MODE_MAPPING.values():
        return mode
    try:
        return consts.MODE_MAPPING[mode.lower()]
    except (KeyError, AttributeError):
        raise ValueError(f'Illegal mode "{mode}". '
                         f'Supported values: {", ".join(sorted(consts.MODE_MAPPING.keys()))}')


def normalize_mask(mask, is_micro):
    """\
    Normalizes the (user specified) mask.

    :param mask: A mask constant
    :type mask: int or None
    :param bool is_micro: Indicates if the mask is meant to be used for a
            Micro QR Code.
    :raises: :py:exc:`ValueError` in case of an invalid mask.
    :rtype: int
    """
    if mask is None:
        return None
    try:
        mask = int(mask)
    except ValueError:
        raise ValueError(f'Invalid data mask "{mask}". '
                         'Must be an integer or a string which represents an integer value.')
    if is_micro:
        if not 0 <= mask < 4:
            raise ValueError(f'Invalid data mask "{mask}" for Micro QR Code. Must be in range 0 .. 3')
    else:
        if not 0 <= mask < 8:
            raise ValueError(f'Invalid data mask "{mask}". Must be in range 0 .. 7')
    return mask


def normalize_errorlevel(error, accept_none=False):
    """\
    Returns a constant for the provided error level.

    This function returns ``None`` if the provided parameter is ``None`` and
    `accept_none` is set to ``True`` (default: ``False``). If `error` is ``None``
    and `accept_none` is ``False`` or if the provided parameter cannot be
    mapped to a valid QR Code error level, a :py:exc:`ValueError` is raised.

    :param error: String or ``None``.
    :param bool accept_none: Indicates if ``None`` is accepted as error level.
    :raises: :py:exc:`ValueError` in case of an invalid mode.
    :rtype: int
    """
    if error is None:
        if not accept_none:
            raise ValueError('The error level must be provided')
        return error
    try:
        return consts.ERROR_MAPPING[error.upper()]
    except (KeyError, AttributeError):
        if error in consts.ERROR_MAPPING.values():
            return error
        raise ValueError(f'Illegal error correction level: "{error}". Supported levels: L, M, Q, H')


def get_mode_name(mode_const):
    """\
    Returns the mode name for the provided mode constant.

    :param int mode_const: The mode constant (see :py:module:`segno.consts`)
    :raises: :py:exc:`ValueError` in case of an unknown mode constant.
    :rtype: str
    """
    for name, val in consts.MODE_MAPPING.items():
        if val == mode_const:
            return name
    raise ValueError(f'Unknown mode "{mode_const}"')


def get_error_name(error_const):
    pass


def get_version_name(version_const):
    """\
    Returns the version name.

    For version 1 .. 40 it returns the version as integer, for Micro QR Codes
    it returns a string like ``M1`` etc.

    :raises: :py:exc:`VersionError`: In case the `version_constant` is unknown.
    :rtype: str or int
    """
    if 0 < version_const < 41:
        return version_const
    for name, v in consts.MICRO_VERSION_MAPPING.items():
        if v == version_const:
            return name
    raise ValueError(f'Unknown version constant "{version_const}"')


_ALPHANUMERIC_PATTERN = re.compile(br'^[' + re.escape(consts.ALPHANUMERIC_CHARS) + br']+\Z')


def is_alphanumeric(data):
    """\
    Returns if the provided `data` can be encoded in "alphanumeric" mode.

    :param bytes data: The data to check.
    :rtype: bool
    """
    return _ALPHANUMERIC_PATTERN.match(data)


def is_kanji(data):
    """\
    Returns if the `data` can be encoded in "kanji" mode.

    :param bytes data: The data to check.
    :rtype: bool
    """
    data_len = len(data)
    if not data_len or data_len % 2:
        return False
    data_iter = iter(data)
    for i in range(0, data_len, 2):
        code = (next(data_iter) << 8) | next(data_iter)
        if not (0x8140 <= code <= 0x9ffc or 0xe040 <= code <= 0xebbf):
            return False
    return True


def find_mode(data):
    """\
    Returns the appropriate QR Code mode (an integer constant) for the
    provided `data`.

    :param bytes data: Data to check.
    :rtype: int
    """
    if data.isdigit():
        return consts.MODE_NUMERIC
    if is_alphanumeric(data):
        return consts.MODE_ALPHANUMERIC
    if is_kanji(data):
        return consts.MODE_KANJI
    return consts.MODE_BYTE


def find_version(segments, error, eci, micro, is_sa=False):
    """\
    Returns the minimal (Micro) QR Code version constant for the provided input.

    :param segments: Iterable of Segment instances.
    :param error: The error correction level constant.
    :type error: int or None
    :param bool eci: Indicates if the ECI mode should be used.
    :param micro: Boolean value if a Micro QR Code should be created or ``None``
    :type micro: bool or None
    :param bool is_sa: Indicator if Structured Append is used.
    :raises: :py:exc:`ValueError` if the content does not fit into a QR Code.
    :rtype: int
    """
    assert not (eci and micro)
    micro_allowed = micro or micro is None
    min_version = consts.VERSION_M1 if micro_allowed else 1
    max_version = consts.VERSION_M4 if micro else 40
    if min_version < 1:
        min_version = max([find_minimum_version_for_mode(mode) for mode in segments.modes])
    if error is not None and micro_allowed:
        min_version = consts.VERSION_M2
    for version in range(min_version, max_version + 1):
        if error is None and version != consts.VERSION_M1:
            error = consts.ERROR_LEVEL_L
        try:
            if consts.SYMBOL_CAPACITY[version][error] >= segments.bit_length_with_overhead(version, eci, is_sa):
                return version
        except KeyError:
            pass
    help_txt = ''
    if micro is None:
        help_txt = '(Micro) '
    elif micro:
        help_txt = 'Micro '
    raise DataOverflowError(f'Data too large. No {help_txt}QR Code can handle the provided data')


def calc_matrix_size(ver):
    """\
    Returns the matrix size according to the provided `version`.

    Note: This function does not check if `version` is actually a valid
    (Micro) QR Code version. Invalid versions like ``41`` may return a
    size as well.

    :param int ver: (Micro) QR Code version constant.
    :rtype: int
    """
    return ver * 4 + 17 if ver > 0 else (ver + 4) * 2 + 9


def calc_structured_append_parity(content):
    pass


def is_mode_supported(mode, ver):
    """\
    Returns if `mode` is supported by `version`.

    Note: This function does not check if `version` is actually a valid
    (Micro) QR Code version. Invalid versions like ``41`` may return an illegal
    value.

    :param int mode: Canonicalized mode.
    :param int or None ver: (Micro) QR Code version constant.
    :rtype: bool
    """
    ver = None if ver > 0 else ver
    try:
        return ver in consts.SUPPORTED_MODES[mode]
    except KeyError:
        raise ValueError(f'Unknown mode "{mode}"')


def find_minimum_version_for_mode(mode):
    """\
    Returns the minimum Micro QR Code version which supports the provided mode.

    :param int mode: Canonicalized mode.
    :rtype: int
    """
    for v in consts.MICRO_VERSIONS:
        if is_mode_supported(mode, v):
            return v
    return 1


def version_range(version):
    """\
    Returns the version range for the provided version. This applies to QR Code
    versions, only.

    :param int version: The QR Code version (1 .. 40)
    :rtype: int
    """
    if 0 < version < 10:
        return consts.VERSION_RANGE_01_09
    elif 9 < version < 27:
        return consts.VERSION_RANGE_10_26
    elif 26 < version < 41:
        return consts.VERSION_RANGE_27_40
    raise ValueError(f'Unknown version "{version}"')


def get_eci_assignment_number(encoding):
    """\
    Returns the ECI number for the provided encoding.

    :param str encoding: A encoding name
    :return str: The ECI number.
    """
    try:
        return consts.ECI_ASSIGNMENT_NUM[codecs.lookup(encoding).name]
    except KeyError:
        raise ValueError(f'Unknown ECI assignment number for encoding "{encoding}".')


def get_data_mask_functions(is_micro):
    """
    Returns the data mask functions.

    ISO/IEC 18004:2015(E) -- 7.8.2 Data mask patterns (page 50)
    Table 10 — Data mask pattern generation conditions (page 50)

    ===============     =====================   =====================================
    QR Code Pattern     Micro QR Code Pattern￼  Condition
    ===============     =====================   =====================================
    000                                         (i + j) mod 2 = 0
    001                 00                      i mod 2 = 0
    010                                         j mod 3 = 0
    011                                         (i + j) mod 3 = 0
    100                 01                      ((i div 2) + (j div 3)) mod 2 = 0
    101                                         (i j) mod 2 + (i j) mod 3 = 0
    110                 10                      ((i j) mod 2 + (i j) mod 3) mod 2 = 0
    111                 11                      ((i+j) mod 2 + (i j) mod 3) mod 2 = 0
    ===============     =====================   =====================================

    :param is_micro: Indicates if data mask functions for a Micro QR Code
            should be returned
    :return: A tuple of functions
    """
    def fn0(i, j):
        pass

    def fn1(i, j):
        pass

    def fn2(i, j):
        pass

    def fn3(i, j):
        pass

    def fn4(i, j):
        pass

    def fn5(i, j):
        pass

    def fn6(i, j):
        pass

    def fn7(i, j):
        pass

    if is_micro:
        return fn1, fn4, fn6, fn7
    return fn0, fn1, fn2, fn3, fn4, fn5, fn6, fn7


class Segments:
    __slots__ = ('bit_length', 'modes', 'segments')

    def __init__(self):
        self.segments = []
        self.bit_length = 0
        self.modes = []

    def add_segment(self, segment):
        """\

        :param _Segment segment: Segment to add.
        """
        if self.segments:
            prev_seg = self.segments[-1]
            if prev_seg.mode == segment.mode and prev_seg.encoding == segment.encoding:
                segment = _Segment(prev_seg.bits + segment.bits,
                                   prev_seg.char_count + segment.char_count,
                                   segment.mode, segment.encoding)
                self.bit_length -= len(prev_seg.bits)
                del self.segments[-1]
                del self.modes[-1]
        self.segments.append(segment)
        self.bit_length += len(segment.bits)
        self.modes.append(segment.mode)

    def __len__(self):
        return len(self.segments)

    def __getitem__(self, item):
        return self.segments[item]

    def __iter__(self):
        return iter(self.segments)

    def bit_length_with_overhead(self, version, eci, is_sa=False):
        overhead = 0
        if eci:
            no_eci_indicators = sum(1 for segment in self.segments
                                    if segment.mode == consts.MODE_BYTE
                                    and segment.encoding != consts.DEFAULT_BYTE_ENCODING)
            overhead += no_eci_indicators * 4  # ECI indicator
            overhead += no_eci_indicators * 8  # ECI assignment no
        if is_sa:
            overhead += 5 * 4
        if version > 0:  # QR Code
            overhead += len(self.modes) * 4
        elif version > consts.VERSION_M1:  # Micro QR Code (M1 has no mode indicator)
            overhead += len(self.modes) * (version + 3)
        ver_range = version_range(version) if version > 0 else version
        overhead += sum(consts.CHAR_COUNT_INDICATOR_LENGTH[mode][ver_range] for mode in self.modes)
        return overhead + self.bit_length


class _Segment(tuple):
    __slots__ = ()

    def __new__(cls, bits, char_count, mode, encoding=None):
        return tuple.__new__(cls, (bits, char_count, mode, encoding))

    bits = property(itemgetter(0))
    char_count = property(itemgetter(1))
    mode = property(itemgetter(2))
    encoding = property(itemgetter(3))


class Buffer:
    __slots__ = ['_data']

    def __init__(self, iterable=()):
        self._data = bytearray(iterable)

    def extend(self, iterable):
        self._data.extend(iterable)

    def append_bits(self, val, length):
        self._data.extend((val >> i) & 1 for i in reversed(range(length)))

    def getbits(self):
        return self._data

    def toints(self):
        """\
        Returns an iterable of integers interpreting the content of `seq`
        as sequence of binary numbers of length 8.
        """
        return (int(''.join(map(str, g)), 2) for g in zip_longest(*[iter(self._data)] * 8, fillvalue=0))

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        return self._data[item]


class _StructuredAppendInfo(tuple):
    __slots__ = ()

    def __new__(cls, number, total, parity):
        """\
        :param int number: Symbol number ``[0 .. 15]``
        :param int total: Total symbol count ``[2 .. 15]``
        :param int parity: Parity data.
        """
        return super().__new__(cls, (consts.MODE_STRUCTURED_APPEND, number, total, parity))

    mode = property(itemgetter(0))
    number = property(itemgetter(1))
    total = property(itemgetter(2))
    parity = property(itemgetter(3))
