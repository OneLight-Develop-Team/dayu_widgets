#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.3
# Email : muyanru345@163.com
###################################################################
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from Qt import QtCore
from Qt import QtWidgets

# Import local modules
from dayu_widgets.divider import MDivider
from dayu_widgets.label import MLabel
from dayu_widgets.message import MMessage
from dayu_widgets.splitter import MSplitter
from dayu_widgets.tab_widget import MTabWidget
from dayu_widgets.text_edit import MTextEdit


class MTabWidgetTest(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MTabWidgetTest, self).__init__(parent)
        self._init_ui()
        self.resize(500, 500)

    def _init_ui(self):
        layout = QtWidgets.QVBoxLayout()
        splitter = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        tab_card = MTabWidget()
        tab_card.addTab(MLabel("test 1"), "Current Element")
        tab_card.addTab(MLabel("test 2"), "Linked Assets")
        tab_card.addTab(MLabel("test 2"), "Hero Shots")
        tab_card.addTab(MLabel("test 3"), "Linked Metadata")

        self.tab_closable = MTabWidget()
        self.tab_closable.setTabsClosable(True)
        self.tab_closable.addTab(MLabel("test 1"), "标签一")
        self.tab_closable.addTab(MLabel("test 2"), "标签二")
        self.tab_closable.addTab(MLabel("test 3"), "标签三")
        self.tab_closable.tabCloseRequested.connect(self.slot_close_tab)
        self.tab_closable.setProperty("draggable", True)

        tab_draggable = MTabWidget()
        tab_draggable.setObjectName("draggable")
        tab_draggable.setProperty("draggable", True)
        tab_draggable.addTab(MTextEdit("Draggable 1"), "拖拽一")
        tab_draggable.addTab(MTextEdit("Draggable 2"), "拖拽二")
        tab_draggable.addTab(MTextEdit("Draggable 3"), "拖拽三")

        tab_container = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab_container)
        tab_layout.addWidget(MDivider("Normal"))
        tab_layout.addWidget(tab_card)
        splitter.addWidget(tab_container)

        tab_container = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab_container)
        tab_layout.addWidget(MDivider("Draggable"))
        tab_layout.addWidget(tab_draggable)
        splitter.addWidget(tab_container)

        tab_container = QtWidgets.QWidget()
        tab_layout = QtWidgets.QVBoxLayout(tab_container)
        tab_layout.addWidget(MDivider("Closable"))
        tab_layout.addWidget(self.tab_closable)
        splitter.addWidget(tab_container)

        layout.addWidget(splitter)
        self.setLayout(layout)

    @QtCore.Slot(int)
    def slot_close_tab(self, index):
        if index > 0:
            print(1)
            text = self.tab_closable.tabText(index)
            print(self.tab_closable.count, index)
            self.tab_closable.removeTab(index)
            MMessage.info("成功关闭一个标签: {}".format(text), closable=True, parent=self)
        else:
            MMessage.warning("请不要关闭第一个标签", closable=True, parent=self)


if __name__ == "__main__":
    # Import local modules
    from dayu_widgets import dayu_theme
    from dayu_widgets.qt import application

    with application() as app:
        test = MTabWidgetTest()
        dayu_theme.apply(test)
        test.show()
