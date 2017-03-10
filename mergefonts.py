#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import re
import types
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import fontforge
import psMat

VERSION = '0.1.0'
FONT_CONFIG = 'fonts.json'
with open(FONT_CONFIG) as fo:
    FONTS_CONTEXT = json.load(fo)


def show_available_fonts():
    print('{0:-^80}'.format(' Available Fonts '))
    for value in FONTS_CONTEXT:
        print('{0:>16}: {1}'.format(value['id'], value['name']))
        if 'description' in value:
            print('{0:>20} {1}'.format('-', value['description']))


def get_context(fid):
    for ctx in FONTS_CONTEXT:
        if ctx['id'] == fid:
            return ctx


def get_glyph_size_info(glyph):
    xmin, ymin, xmax, ymax = glyph.boundingBox()
    return {
        'width': max(glyph.width, xmax - xmin),
        'vwidth': glyph.vwidth,
        'height': ymax - ymin,
        'xmin': xmin,
        'ymin': ymin,
        'xmax': xmax,
        'ymax': ymax,
    }


def _get_font_max_size_info(font, start, end):
    data = {
        'width': 0,
        'vwidth': 0,
        'height': 0,
        'xmin': 0,
        'ymin': 0,
        'xmax': 0,
        'ymax': 0,
    }
    for code in range(start, end + 1):
        try:
            _data = get_glyph_size_info(font[code])
            for k, v in _data.items():
                if abs(v) > abs(data[k]):
                    data[k] = v
        except TypeError:
            continue
    return data


def get_size_hints(font):
    # return hints for glyph transform
    return {
        'half': _get_font_max_size_info(font, 0x23, 0x7e),
        'full': _get_font_max_size_info(font, 0xff01, 0xff5e),
        'ascent': font.hhea_ascent,
        'descent': font.hhea_descent,
    }


def get_height(font):
    return font.hhea_ascent + abs(font.hhea_descent)


def get_font_name_info(font):
    family = font.familyname
    fullname = font.fullname
    sub_family = 'Regular'
    name = font.fontname
    _, fallback_style = re.match('^([^-]*).*?([^-]*(?!.*-))$', name).groups()
    try:
        sub_family_tuple_index = [x[1] for x in font.sfnt_names].index('SubFamily')
        sub_family = font.sfnt_names[2][sub_family_tuple_index]
    except IndexError:
        pass
    if sub_family == 'Regular':
        sub_family = fallback_style
    family = re.sub(r'[ _-]?{0}$'.format(sub_family), '', family, flags=re.IGNORECASE)
    fullname = re.sub(r'[ _-]?{0}$'.format(sub_family), '', fullname, flags=re.IGNORECASE)
    name = re.sub(r'[ _-]?{0}$'.format(sub_family), '', name, flags=re.IGNORECASE)
    return name, family, fullname, sub_family


def display_font_details(font):
    print('{0:-^80}:'.format(' Font Details: '))
    for name in dir(font):
        if name.startswith('_'):
            continue
        value = getattr(font, name)
        if type(value) in (types.IntType, types.FloatType, types.StringType, types.UnicodeType):
            print('{0:>32}: {1}'.format(name, value))


def preview(font, ctx):
    unicode_range = ctx.get('unicode_range', [])
    ext_start = 0
    ext_end = 0
    if len(unicode_range) >= 1:
        ext_start = int(unicode_range[0], 16)
    if len(unicode_range) >= 2:
        ext_end = int(unicode_range[1], 16)
    start = ext_start
    end = ext_end
    remap_start_point = ctx.get('remap_start_point', None)
    if remap_start_point is not None:
        start = int(remap_start_point, 16)
        end = start + (ext_end - ext_start)
    if ext_start is 0:
        font.selection.all()
    else:
        font.selection.select(('ranges', 'unicode'), start, end)
    hints = get_size_hints(font)
    length = 0
    line = ''
    print('{0:-^80}'.format(' ' + ctx['id'] + ' '))
    for glyph in list(font.selection.byGlyphs):
        line += unichr(glyph.encoding)
        if glyph.width < hints['full']['width']:
            # half width
            line += ' '
            pass
        length += 1
        if length is 40:
            print(line.encode('utf-8'))
            length = 0
            line = ''
    if length > 0:
        print(line.encode('utf-8'))


def merge(base_font, font, ctx):
    unicode_range = ctx.get('unicode_range', [])
    glyph_scale = ctx.get('scale', 1.0)
    ext_start = 0
    ext_end = 0
    if len(unicode_range) >= 1:
        ext_start = int(unicode_range[0], 16)
    if len(unicode_range) >= 2:
        ext_end = int(unicode_range[1], 16)
    base_start = ext_start
    remap_start_point = ctx.get('remap_start_point', None)
    if remap_start_point is not None:
        base_start = int(remap_start_point, 16)
    hints = get_size_hints(base_font)
    base_font_height = get_height(base_font)
    font_height = get_height(font)
    # scale transform
    scale_ratio_x = float(base_font.em) / font.em
    scale_ratio_y = float(base_font_height) / font_height
    scale = psMat.scale(scale_ratio_x * glyph_scale, scale_ratio_y * glyph_scale)
    if ext_start is 0:
        font.selection.all()
    else:
        font.selection.select(('ranges', 'unicode'), ext_start, ext_end)
    for glyph in list(font.selection.byGlyphs):
        index = base_start + (glyph.encoding - ext_start)
        font.selection.select(glyph.encoding)
        font.copy()
        base_font.selection.select(index)
        base_font.paste()
        _glyph = base_font[index]
        _glyph.transform(scale)
        _glyph.glyphname = glyph.glyphname
        info = get_glyph_size_info(_glyph)
        move_x = 0
        move_y = 0
        if hints['ascent'] < info['ymax']:
            move_y = hints['ascent'] - info['ymax']
        if glyph_scale < 1.0 and ctx.get('adjust_position', False):
            # TODO: translate X
            move_x += info['width'] * (1.0 - glyph_scale) / 2.0
            move_y -= info['height'] * (1.0 - glyph_scale) / 2.0
        _glyph.transform(psMat.translate(move_x, move_y))
        info = get_glyph_size_info(_glyph)
        hint = hints['half']['width'] * 1.05 >= info['width'] and hints['half'] or hints['full']
        _glyph.width = hint['width']
        _glyph.vwidth = hint['vwidth']


def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    ids = [font['id'] for font in FONTS_CONTEXT]
    parser.add_argument('base_fonts', metavar='BASE_FONT', nargs='*', default=[],
                        help='target fonts')
    parser.add_argument('-V', '--version', dest='show_version', action='store_true', default=False,
                        help='show version')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true', default=False,
                        help='verbose mode')
    parser.add_argument('-x', '--ext_fonts', dest='ext_fonts', metavar='EXT_FONT', nargs='*', choices=ids, default=[],
                        help='extend fonts')
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
    args = parser.parse_args()

    if args.list_fonts:
        show_available_fonts()
        return

    if args.show_version:
        print('fontmerger v{0}'.format(VERSION))
        return

    if len(args.base_fonts) is 0 and len(args.ext_fonts) is 0:
        parser.print_help()
        return

    ids = args.ext_fonts
    if args.all:
        ids = [c['id'] for c in FONTS_CONTEXT]

    for path in args.base_fonts:
        base_font = fontforge.open(path)
        if args.info:
            display_font_details(base_font)
            continue
        fontname, familyname, fullname, subfamily = get_font_name_info(base_font)
        base_font.encoding = 'UnicodeFull'
        if args.suffix:
            familyname = '{0} {1}'.format(familyname, args.suffix)
            fullname = '{0} {1}'.format(familyname, subfamily)
            fontname = '{0}-{1}-{2}'.format(fontname, args.suffix, subfamily)
            base_font.familyname = familyname
            base_font.fullname = fullname
            base_font.fontname = fontname
            base_font.appendSFNTName('English (US)', 'Preferred Family', familyname)
            base_font.appendSFNTName('English (US)', 'Compatible Full', fullname)
            base_font.appendSFNTName('English (US)', 'SubFamily', subfamily)

        for fid in ids:
            ctx = get_context(fid)
            if ctx:
                if args.preview_fonts:
                    preview(base_font, ctx)
                    continue
                ext_font = fontforge.open(ctx['filename'])
                merge(base_font, ext_font, ctx)
                if ext_font.copyright and ext_font.copyright not in base_font.copyright:
                    base_font.copyright += '\n' + ext_font.copyright
                ext_font.close()

        if not args.preview_fonts:
            extension = os.path.splitext(base_font.path)[1]
            font_filename = os.path.join(args.outputdir, base_font.fontname + extension)
            base_font.generate(font_filename, flags=('opentype',))
            print('"{0}" generated.'.format(font_filename))
        base_font.close()


if __name__ == '__main__':
    main()
