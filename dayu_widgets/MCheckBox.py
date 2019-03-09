#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.2
# Email : muyanru345@163.com
###################################################################

from MTheme import global_theme
from qt import *
from . import STATIC_FOLDERS

qss = '''
QCheckBox {{
    spacing: 4px;
    {text_font}
    {font_family}
}}
QCheckBox:disabled {{
    color: {disabled};
}}

QCheckBox::indicator{{
    width: 13px;
    height: 13px;
    border-radius: 2px;
    border: 1px solid {border};
    background-color: white;
}}
QCheckBox::indicator:disabled{{
    border: 1px solid {border};
    background-color: {background_selected};
}}

QCheckBox::indicator:hover{{
    border: 1px solid {primary_light};
    background-color: white;
}}

QCheckBox::indicator:checked{{
    background-color: {primary};
    image: url(check.svg);
}}

QCheckBox::indicator:checked:disabled{{
    background-color: {disabled};
}}

QCheckBox::indicator:indeterminate {{
    background-color: {primary};
    image: url(minus.svg);
}}

QCheckBox::indicator:indeterminate:disabled {{
    background-color: {disabled};
}}
'''.format(**global_theme)
qss = qss.replace('url(', 'url({}/'.format(STATIC_FOLDERS[0].replace('\\', '/')))


@property_mixin
class MCheckBox(QCheckBox):
    def __init__(self, text='', parent=None):
        super(MCheckBox, self).__init__(text=text, parent=parent)
        self.setStyleSheet(qss)

    def enterEvent(self, *args, **kwargs):
        QApplication.setOverrideCursor(Qt.PointingHandCursor if self.isEnabled() else Qt.ForbiddenCursor)
        return super(MCheckBox, self).enterEvent(*args, **kwargs)

    def leaveEvent(self, *args, **kwargs):
        QApplication.restoreOverrideCursor()
        return super(MCheckBox, self).leaveEvent(*args, **kwargs)