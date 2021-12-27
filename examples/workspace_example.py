#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: TimmyLiang
# Date  : 2021.12
# Email : 820472580@qq.com
###################################################################
"""
Example code for MSplitter
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.text_edit import MTextEdit
from dayu_widgets.workspace import MWorkspace


class SplitterExample(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SplitterExample, self).__init__(parent)
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        workspace = MWorkspace()
        # workspace.addTab(MTextEdit(), "拖拽一")
        # workspace.addTab(MTextEdit(), "拖拽二")
        # workspace.addTab(MTextEdit(), "拖拽三")

        workspace.addWidget(MTextEdit("widget1"), "test")
        workspace.addWidget(MTextEdit("widget2"))
        workspace.addWidget(MTextEdit("widget3"))
        self.resize(800, 800)

        layout.addWidget(workspace)


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets.qt import application

    with application() as app:
        test = SplitterExample()
        dayu_theme.apply(test)
        test.show()
