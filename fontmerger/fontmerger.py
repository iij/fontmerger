#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fontforge
import os
import psMat
import re
import sys
from logging import getLogger


class MergingContext(object):
    def __init__(self, **kwargs):
        self.id = ''
        self.filename = ''
        self.name = ''
        self.description = ''
        self.unicode_range = []
        self.remap_start_point = None
        self.scale = 1.0
        self.adjust_position = False

        for key, value in kwargs.items():
            setattr(self, key, value)


class GlyphSizeInfo(object):
    def __init__(self, glyph):
        """:param fontforge.glyph glyph: Glyph object"""
        xmin, ymin, xmax, ymax = glyph.boundingBox()
        self.glyph_width = glyph.width
        self.glyph_vwidth = glyph.vwidth
        self.width = xmax - xmin
        self.height = ymax - ymin
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax


class FontSizeHints(object):
    def __init__(self, font):
        """Font's size hints
        :param fontforge.font font: a font object"""
        self.font = font
        self._half = None
        self._full = None
        self.ascent = font.hhea_ascent
        self.descent = font.hhea_descent

    @property
    def half(self):
        """returns size info for half-width font
        :return GlyphSizeInfo: glyph's size info"""
        if not self._half:
            self._half = _get_font_max_size_info(self.font, 0x23, 0x7e)
        return self._half

    @property
    def full(self):
        """returns size info for full-width font
        :return: GlyphSizeInfo: glyph's size info
        """
        if not self._full:
            self._full = _get_font_max_size_info(self.font, 0xff01, 0xff5e)
        return self._full


def display_unicode_utf8(ctx, fd=sys.stdout):
    """display unicode characters as UTF-8
    :param MergingContext ctx: a merging font context
    :param file fd: display target"""
    font = fontforge.open(ctx.filename)
    unicode_range = ctx.unicode_range
    start = 0
    end = 0
    if len(unicode_range) >= 1:
        start = int(unicode_range[0], 16)
    if len(unicode_range) >= 2:
        end = int(unicode_range[1], 16)
    remap_start_point = ctx.remap_start_point
    delta = 0
    if remap_start_point is not None:
        delta = int(remap_start_point, 16) - start
    if start is 0:
        font.selection.all()
    else:
        font.selection.select(('ranges', 'unicode'), start, end)
    length = 0
    line = ''
    fd.write('{0:-^80}\n'.format(' ' + ctx.id + ' '))
    for glyph in list(font.selection.byGlyphs):
        line += unichr(glyph.encoding + delta)
        info = get_glyph_size_info(glyph)
        if info.width <= font.em / 2:
            # half width
            line += ' '
        length += 1
        if length is 40:
            fd.write(line.encode('utf-8') + '\n')
            length = 0
            line = ''
    if length > 0:
        fd.write(line.encode('utf-8') + '\n')
    fd.flush()
    font.close()


def get_glyph_size_info(glyph):
    """return a glyph size information(position, height, width)
    :param fontforge.glyph glyph: glyph object
    :return GlyphSizeInfo glyph: glyph's size information"""
    return GlyphSizeInfo(glyph)


def _get_font_max_size_info(font, start, end):
    """return size information for biggest glyph
    :param fontforge.font font: font object
    :param int start: unicode start point
    :param int end: unicode end point
    :return GlyphSizeInfo: biggest glyph size info"""
    info = None
    for code in range(start, end + 1):
        try:
            _info = get_glyph_size_info(font[code])
            if info is None:
                info = _info
                continue
            for key in dir(_info):
                a = getattr(_info, key)
                b = getattr(info, key)
                if abs(a) > abs(b):
                    setattr(info, key, a)
        except TypeError:
            continue
    return info


def get_size_hints(font):
    """return font's size hints
    :param fontforge.font font: a font object
    :return hints for glyph transform"""
    return FontSizeHints(font)


def get_height(font):
    """return font height
    :param fontforge.font font: a font object
    :return font height"""
    return font.hhea_ascent + abs(font.hhea_descent)


def get_font_name_info(font):
    """return font name information
    :param fontforge.font font: a font object
    :return tuple of (font name, font family name, full name, sub-family name)"""
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


class FontMerger(object):
    def __init__(self, path):
        self.log = getLogger()
        self.base_font_path = path
        font = fontforge.open(path)
        if font.iscid:
            raise RuntimeError('CID font is not supported yet.')
        font.encoding = 'UnicodeFull'
        self.base_font = font
        self._hints = None

    def rename(self, suffix=None):
        fontname, familyname, fullname, subfamily = get_font_name_info(self.base_font)
        if suffix:
            fontname = '{0}-{1}-{2}'.format(fontname, suffix, subfamily)
            familyname = '{0} {1}'.format(familyname, suffix)
            fullname = '{0} {1}'.format(familyname, subfamily)
        self.base_font.familyname = familyname
        self.base_font.fullname = fullname
        self.base_font.fontname = fontname
        self.base_font.appendSFNTName('English (US)', 'Preferred Family', familyname)
        self.base_font.appendSFNTName('English (US)', 'Compatible Full', fullname)
        self.base_font.appendSFNTName('English (US)', 'SubFamily', subfamily)

    @property
    def hints(self):
        if not self._hints:
            self._hints = get_size_hints(self.base_font)
        return self._hints

    def get_hint(self, width):
        if self.hints.half.width * 1.2 >= width:
            return self.hints.half
        return self.hints.full

    def merge_one(self, ctx):
        self.log.debug('"%s" merging...', ctx.filename)
        font = fontforge.open(ctx.filename)
        unicode_range = ctx.unicode_range
        glyph_scale = ctx.scale
        ext_start = 0
        ext_end = 0
        if len(unicode_range) >= 1:
            ext_start = int(unicode_range[0], 16)
        if len(unicode_range) >= 2:
            ext_end = int(unicode_range[1], 16)
        base_start = ext_start
        remap_start_point = ctx.remap_start_point
        if remap_start_point is not None:
            base_start = int(remap_start_point, 16)
        base_font_height = get_height(self.base_font)
        font_height = get_height(font)

        # scale transform
        scale_ratio_x = round(float(self.base_font.em) / font.em, 3)
        scale_ratio_y = round(float(base_font_height) / font_height, 3)
        scale = psMat.scale(scale_ratio_x * glyph_scale, scale_ratio_y * glyph_scale)
        if ext_start is 0:
            font.selection.all()
        else:
            font.selection.select(('ranges', 'unicode'), ext_start, ext_end)

        # copy and transform glyphs
        for glyph in list(font.selection.byGlyphs):
            index = base_start + (glyph.encoding - ext_start)
            font.selection.select(glyph.encoding)
            font.copy()
            self.base_font.selection.select(index)
            self.base_font.paste()
            _glyph = self.base_font[index]
            _glyph.transform(scale)
            _glyph.glyphname = glyph.glyphname
            info = get_glyph_size_info(_glyph)
            move_x = 0
            move_y = 0
            if self.hints.ascent < info.ymax:
                move_y = self.hints.ascent - info.ymax
            if glyph_scale < 1.0 and ctx.adjust_position:
                move_x += info.width * (1.0 - glyph_scale) / 2.0
                move_y -= info.height * (1.0 - glyph_scale) / 2.0
            info = get_glyph_size_info(_glyph)
            if info.width + move_x < self.base_font.em:
                _glyph.left_side_bearing += move_x
            hint = self.get_hint(info.width)
            if hint.glyph_width < info.width and ctx.adjust_position:
                delta = info.width - hint.glyph_width
                move_x += 1.0 - (delta / hint.glyph_width)
            _glyph.transform(psMat.translate(move_x, move_y))
            _glyph.width = hint.glyph_width
            _glyph.vwidth = hint.glyph_vwidth

        # add copyright
        if font.copyright and font.copyright not in self.base_font.copyright:
            self.base_font.copyright += '\n' + font.copyright
        font.close()
        self.log.debug('"%s" merged.', ctx.filename)

    def merge(self, contexts=()):
        for ctx in contexts:
            self.merge_one(ctx)

    def generate(self, output_dir):
        ext = os.path.splitext(self.base_font.path)[1]
        filename = os.path.join(output_dir, self.base_font.fontname + ext)
        self.base_font.generate(filename, flags=('opentype',))
        return filename

    def close(self):
        self.base_font.close()
