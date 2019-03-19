#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.3
# Email : muyanru345@163.com
###################################################################

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
except:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide.QtWebKit import *
    from PySide.QtSvg import *
import os


class MView(object):
    LargeSize = 'large'
    DefaultSize = 'default'
    SmallSize = 'small'
    TinySize = 'tiny'


class MCacheDict(object):
    _render = QSvgRenderer()

    def __init__(self, cls):
        super(MCacheDict, self).__init__()
        self.cls = cls
        self._cache_pix_dict = {}

    def _render_svg(self, svg_path, replace_color=None):
        if (self.cls is QIcon) and (replace_color is None):
            return QIcon(svg_path)
        with open(svg_path, 'r+') as f:
            data_content = f.read()
            if replace_color is not None:
                data_content = data_content.replace('#555555', replace_color)
            self._render.load(QByteArray(data_content))
            pix = QPixmap(128, 128)
            pix.fill(Qt.transparent)
            painter = QPainter(pix)
            self._render.render(painter)
            painter.end()
            if self.cls is QPixmap:
                return pix
            else:
                return self.cls(pix)

    def __call__(self, path, color=None):
        assert isinstance(path, basestring)
        from dayu_widgets import STATIC_FOLDERS
        full_path = next((os.path.join(prefix, path) for prefix in [''] + STATIC_FOLDERS if
                          os.path.isfile(os.path.join(prefix, path))), path)
        key = u'{}{}'.format(full_path.lower(), color or '')
        pix_map = self._cache_pix_dict.get(key, None)
        if pix_map is None:
            if full_path.endswith('svg'):
                pix_map = self._render_svg(full_path, color)
            else:
                pix_map = self.cls(full_path)
            self._cache_pix_dict.update({key: pix_map})
        return pix_map


MPixmap = MCacheDict(QPixmap)
MIcon = MCacheDict(QIcon)
