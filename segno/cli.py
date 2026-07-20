#!/usr/bin/env python
import os
import sys
import argparse
import segno
from segno import writers

_EXT_TO_KW_MAPPING = {}


def _get_args(func):
    pass


for ext, func in writers._VALID_SERIALIZERS.items():
    kws = set(_get_args(func))
    try:
        kws.update(_get_args(func.__wrapped__))
    except AttributeError:
        pass
    _EXT_TO_KW_MAPPING[ext] = frozenset(kws)

del writers


def make_parser():
    pass


def parse(args):
    pass


def build_config(config, filename=None):
    pass


def make_code(config):
    pass


def main(args=sys.argv[1:]):
    pass


class _AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self


if __name__ == '__main__':
    main()
