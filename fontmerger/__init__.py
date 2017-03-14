# -*- coding: utf-8 -*-
import json
import sys
import types
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from fontmerger import MergingContextHolder, MergingContext, FontMerger

VERSION = '0.1.0'


def show_version():
    print('fontmerger v{0}'.format(VERSION))


def show_font_details(font):
    print('{0:-^80}:'.format(' Font Details: '))
    for name in dir(font):
        if name.startswith('_'):
            continue
        value = getattr(font, name)
        if type(value) in (types.IntType, types.FloatType, types.StringType, types.UnicodeType):
            print('{0:>32}: {1}'.format(name, value))


def show_available_fonts(context_holder):
    print('{0:-^80}'.format(' Available Fonts '))
    for ctx in context_holder.contexts:
        print('{0:>16}: {1}'.format(ctx.id, ctx.name))
        if ctx.description:
            print('{0:>20} {1}'.format('-', ctx.description))


def get_argparser():
    parser = ArgumentParser(prog='fontmerger', formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('base_fonts', metavar='BASE_FONT', nargs='*', default=[],
                        help='target fonts')
    parser.add_argument('-V', '--version', dest='show_version', action='store_true', default=False,
                        help='show version')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='verbose mode')
    parser.add_argument('-c', '--config', dest='config', default='./fonts.json',
                        help='a configuration file which define font merge context by JSON format')
    parser.add_argument('-x', '--ext-fonts', dest='ext_fonts', metavar='EXT_FONT_ID', nargs='*', default=[],
                        help='a list of font identifier that merging fonts')
    parser.add_argument('-i', '--info', dest='info', action='store_true', default=False,
                        help='show base font information')
    parser.add_argument('-o', '--output', dest='outputdir', metavar='OUTPUT_DIR', default='./',
                        help='output directory')
    parser.add_argument('-l', '--list', dest='list_fonts', action='store_true', default=False,
                        help='show available additional fonts')
    parser.add_argument('-p', '--preview', dest='preview_fonts', action='store_true', default=False,
                        help='preview fonts')
    parser.add_argument('--all', dest='all', action='store_true', default=False,
                        help='extend all fonts')
    parser.add_argument('--suffix', dest='suffix',
                        help='font name suffix')
    return parser


def main():
    parser = get_argparser()
    args = parser.parse_args()
    holder = MergingContextHolder()
    with open(args.config) as fo:
        xs = json.load(fo)
        for x in xs:
            ctx = MergingContext(**x)
            ctx.enabled = args.all or ctx.id in args.ext_fonts
            holder.add(ctx)
    if args.list_fonts:
        show_available_fonts(holder)
        return 0
    if args.show_version:
        show_version()
        return 0
    if len(args.base_fonts) is 0 and len(args.ext_fonts) is 0:
        parser.print_help()
        return 1
    for path in args.base_fonts:
        merger = FontMerger(path, holder)
        if args.info:
            show_font_details(merger.base_font)
            continue
        if args.preview_fonts:
            merger.preview()
            continue
        merger.merge()
        merger.rename(args.suffix)
        merger.generate(args.outputdir)
        merger.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
