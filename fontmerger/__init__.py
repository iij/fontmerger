# -*- coding: utf-8 -*-
import json
import sys
import traceback
import types
import logging
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from fontmerger import MergingContext, FontMerger, display_unicode_utf8

VERSION = '0.2.1'


def show_version():
    print('fontmerger v{0}'.format(VERSION))


def show_font_details(font):
    print('{0:-^80}:'.format(' Font Details: '))
    for name in dir(font):
        if name.startswith('_'):
            continue
        value = getattr(font, name)
        if name == 'sfnt_names':
            for locale, _name, _value in value:
                print('{0:>32}: {1} = {2}'.format(locale, _name, _value))
        if type(value) in (types.IntType, types.FloatType,) + types.StringTypes:
            print('{0:>32}: {1}'.format(name, value))


def show_available_fonts(contexts=()):
    print('{0:-^80}'.format(' Available Fonts '))
    for ctx in contexts:
        print('{0:>16}: {1}'.format(ctx.id, ctx.name))
        if ctx.description:
            print('{0:>20} {1}'.format('-', ctx.description))


def opt_parser():
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
    parser.add_argument('--suffix', dest='suffix', help='font name suffix')
    parser.add_argument('--debug', dest='debug', action='store_true', default=False, help='debug mode')
    return parser


def main():
    parser = opt_parser()
    args = parser.parse_args()
    contexts = []
    with open(args.config) as fo:
        xs = json.load(fo)
        for x in xs:
            ctx = MergingContext(**x)
            if args.list_fonts or args.all or ctx.id in args.ext_fonts:
                contexts.append(ctx)
    if args.list_fonts:
        show_available_fonts(contexts)
        return 0
    if args.verbose:
        logging.basicConfig(format='%(message)s', stream=sys.stdout)
    if args.show_version:
        show_version()
        return 0
    if len(args.base_fonts) is 0 and len(contexts) is 0:
        parser.print_help()
        return 1
    if args.preview_fonts:
        for ctx in contexts:
            display_unicode_utf8(ctx, sys.stdout)
        return 0
    log = logging.getLogger()
    for path in args.base_fonts:
        log.info('"%s" merging fonts...', path)
        try:
            merger = FontMerger(path)
            if args.info:
                show_font_details(merger.base_font)
                continue
            merger.merge(contexts)
            merger.rename(args.suffix)
            filename = merger.generate(args.outputdir)
            merger.close()
            log.info('"%s" generated.', filename)
        except Exception, e:
            if args.debug:
                traceback.print_exc(file=sys.stdout)
            else:
                log.error(e)
    return 0


if __name__ == '__main__':
    sys.exit(main())
