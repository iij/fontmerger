#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fontforge
import os
import psMat
import re


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


class MergingContext(object):
    def __init__(self, **kwargs):
        self.id = None
        self.name = ''
        self.description = ''
        self.unicode_range = []
        self.remap_start_point = None
        self.scale = 1.0
        self.adjust_position = False
        self.enabled = False

        for key, value in kwargs.items():
            setattr(self, key, value)


class MergingContextHolder(object):
    def __init__(self, contexts=None):
        self.contexts = contexts or []

    def add(self, ctx):
        self.contexts.append(ctx)

    @property
    def ids(self):
        return [ctx.id for ctx in self.contexts]

    @property
    def enable_contexts(self):
        return [ctx for ctx in self.contexts if ctx.enabled]

    def get_by_id(self, fid):
        for ctx in self.contexts:
            if ctx.id == fid:
                return ctx


class FontMerger(object):
    def __init__(self, font_filename, context_holder, verbose=False):
        self.base_font = fontforge.open(font_filename)
        self.context_holder = context_holder
        self.verbose = verbose
        self._hints = None
        self._prepared = False

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

    def prepare(self):
        if not self._prepared:
            self.base_font.encoding = 'UnicodeFull'
            self._hints = get_size_hints(self.base_font)
            self._prepared = True

    def preview_one(self, ctx):
        self.prepare()
        unicode_range = ctx.unicode_range
        ext_start = 0
        ext_end = 0
        if len(unicode_range) >= 1:
            ext_start = int(unicode_range[0], 16)
        if len(unicode_range) >= 2:
            ext_end = int(unicode_range[1], 16)
        start = ext_start
        end = ext_end
        remap_start_point = ctx.remap_start_point
        if remap_start_point is not None:
            start = int(remap_start_point, 16)
            end = start + (ext_end - ext_start)
        if ext_start is 0:
            self.base_font.selection.all()
        else:
            self.base_font.selection.select(('ranges', 'unicode'), start, end)
        length = 0
        line = ''
        print('{0:-^80}'.format(' ' + ctx.id + ' '))
        for glyph in list(self.base_font.selection.byGlyphs):
            line += unichr(glyph.encoding)
            if glyph.width < self._hints['full']['width']:
                # half width
                line += ' '
            length += 1
            if length is 40:
                print(line.encode('utf-8'))
                length = 0
                line = ''
        if length > 0:
            print(line.encode('utf-8'))

    def preview(self):
        for ctx in self.context_holder.enable_contexts:
            self.preview_one(ctx)

    def merge_one(self, ctx):
        self.prepare()
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
        scale_ratio_x = float(self.base_font.em) / font.em
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
            self.base_font.selection.select(index)
            self.base_font.paste()
            _glyph = self.base_font[index]
            _glyph.transform(scale)
            _glyph.glyphname = glyph.glyphname
            info = get_glyph_size_info(_glyph)
            move_x = 0
            move_y = 0
            if self._hints['ascent'] < info['ymax']:
                move_y = self._hints['ascent'] - info['ymax']
            if glyph_scale < 1.0 and ctx.adjust_position:
                move_x += info['width'] * (1.0 - glyph_scale) / 2.0
                move_y -= info['height'] * (1.0 - glyph_scale) / 2.0
            info = get_glyph_size_info(_glyph)
            if info['width'] + move_x < self.base_font.em:
                _glyph.left_side_bearing += move_x
            hint = self._hints['half']['width'] * 1.05 >= info['width'] and self._hints['half'] or self._hints['full']
            _glyph.transform(psMat.translate(move_x, move_y))
            _glyph.width = hint['width']
            _glyph.vwidth = hint['vwidth']

        if font.copyright and font.copyright not in self.base_font.copyright:
            self.base_font.copyright += '\n' + font.copyright
        font.close()

    def merge(self):
        for ctx in self.context_holder.enable_contexts:
            self.merge_one(ctx)

    def generate(self, output_dir):
        extension = os.path.splitext(self.base_font.path)[1]
        font_filename = os.path.join(output_dir, self.base_font.fontname + extension)
        self.base_font.generate(font_filename, flags=('opentype',))
        print('"{0}" generated.'.format(font_filename))

    def close(self):
        self.base_font.close()
