#!/usr/bin/env python
# -*- coding: utf-8 -*-
###################################################################
# Author: Mu yanru
# Date  : 2019.2
# Email : muyanru345@163.com
###################################################################

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from functools import partial

# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets

# Import local modules
from dayu_widgets.menu import MMenu
from dayu_widgets.mixin import copy_mixin
from dayu_widgets.mixin import property_mixin
from dayu_widgets.splitter import MSplitter
from dayu_widgets.tab_widget import MDraggableTabBar
from dayu_widgets.tab_widget import MDraggableTabWidget
from dayu_widgets.tool_button import MToolButton


@property_mixin
class MBarOverlay(QtWidgets.QWidget):
    def __init__(self, parent):
        super(MBarOverlay, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda: print(1))

        self.tab = parent

        layout = QtWidgets.QHBoxLayout()
        self.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        down_tool = MToolButton().svg("down_line.svg").small()
        down_tool.clicked.connect(self.slot_tab_menu)
        float_tool = MToolButton().svg("float.svg").small()
        float_tool.clicked.connect(lambda *args: parent.slot_dropped_outside())
        close_tool = MToolButton().svg("close_line.svg").small()
        close_tool.clicked.connect(parent.deleteLater)

        layout.addStretch()
        layout.addWidget(down_tool)
        layout.addWidget(float_tool)
        layout.addWidget(close_tool)

        self.opacity_widget = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_widget)
        self.setAutoFillBackground(True)

        self._opacity_anim = QtCore.QPropertyAnimation(self.opacity_widget, b"opacity")
        self.setProperty("animOpacityDuration", 300)
        self.setProperty("animOpacityCurve", "OutCubic")
        self.setProperty("animOpacityStart", 0)
        self.setProperty("animOpacityEnd", 1)
        self.setProperty("opacityAnimatable", False)

    def _set_opacityAnimatable(self, value):
        self.opacity_widget.setOpacity(0 if value else 1)

    def _set_animOpacityDuration(self, value):
        self._opacity_anim.setDuration(value)

    def _set_animOpacityCurve(self, value):
        curve = getattr(QtCore.QEasingCurve, value, None)
        if not curve:
            raise TypeError("Invalid QEasingCurve")
        self._opacity_anim.setEasingCurve(curve)

    def _set_animOpacityStart(self, value):
        self._opacity_anim.setStartValue(value)

    def _set_animOpacityEnd(self, value):
        self._opacity_anim.setEndValue(value)

    def eventFilter(self, obj, event):
        if event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Paint):
            self.move(obj.bar.width(), 0)
            self.setFixedWidth(max(0, obj.width() - obj.bar.width()))
            self.setFixedHeight(obj.bar.height())
        if self.property("opacityAnimatable"):
            if event.type() == QtCore.QEvent.Enter:
                self._opacity_anim.setDirection(QtCore.QAbstractAnimation.Forward)
                self._opacity_anim.start()
            elif event.type() == QtCore.QEvent.Leave:
                self._opacity_anim.setDirection(QtCore.QAbstractAnimation.Backward)
                self._opacity_anim.start()

        return False

    def slot_tab_menu(self):
        menu = MMenu(parent=self)
        menu.setProperty("searchable", True)
        for index in range(self.tab.count()):
            text = self.tab.tabText(index)
            action = menu.addAction(text)
            action.triggered.connect(partial(self.tab.setCurrentIndex, index))
        menu.exec_(QtGui.QCursor.pos())


class MWorkspaceTabWidget(MDraggableTabWidget):
    def __init__(self, *args, **kwargs):
        super(MWorkspaceTabWidget, self).__init__(*args, **kwargs)

        self.bar_overlay = MBarOverlay(self)
        self.setProperty("showBarOverlay", False)
        self.setProperty("autoHideBarOverlay", False)

    def _set_showBarOverlay(self, value):
        self.bar_overlay.setVisible(value)

    def _set_autoHideBarOverlay(self, value):
        self.bar_overlay.setProperty("opacityAnimatable", value)


@copy_mixin
@property_mixin
class MWorkspace(MSplitter):

    sig_child_removed = QtCore.Signal()
    DEFAULT_TAB_TITLE = "null"

    def __init__(self, *args, **kwargs):
        super(MWorkspace, self).__init__(*args, **kwargs)
        self.setProperty("is_child_removed", False)
        self.sig_child_removed.connect(self.slot_child_removed)
        self.setProperty("renameable", True)
        self.setProperty("showBarOverlay", True)
        self.setProperty("autoHideBarOverlay", True)

    @QtCore.Slot()
    def slot_child_removed(self):

        count = self.count()
        # print("child removed", count)
        if not count:
            self.setParent(None)
        elif count == 1:
            # print("clean")
            parent = self.parent()
            if isinstance(parent, MWorkspace):
                index = parent.indexOf(self)
                super(MWorkspace, parent).insertWidget(index, self.widget(0))

    def event(self, event):
        if event.type() == QtCore.QEvent.ChildRemoved:
            if not self.property("is_child_removed"):
                setter = partial(self.setProperty, "is_child_removed", False)
                QtCore.QTimer.singleShot(0, setter)
                QtCore.QTimer.singleShot(0, self.sig_child_removed.emit)
            self.setProperty("is_child_removed", True)

        return super(MWorkspace, self).event(event)

    def slot_border_drop(self, drag_widget, index, direction):
        drop_widget = self.sender()
        drop_parent = drop_widget.parent()
        # drag_parent = drag_widget.parent()
        drop_id = drop_parent.indexOf(drop_widget)
        print("drop_id", drop_id)

        orient = QtCore.Qt.Vertical if direction in [1, 3] else QtCore.Qt.Horizontal
        is_after = direction in [0, 1]
        if orient == drop_parent.orientation():
            insert_id = drop_id
            tab_widget = drag_widget
            if drag_widget.count() > 1:
                widget = drag_widget.widget(index)
                label = drag_widget.tabText(index)
                tab_widget = self._create_tab_widget(widget, label, drag_widget)

            # if drag_widget is not drop_widget:
            #     if is_after:
            #         insert_id += 1
            #     else:
            #         insert_id -= 1
            print("insert_id", insert_id)
            return super(MWorkspace, drop_parent).insertWidget(insert_id, tab_widget)

        workspace = self.copy()
        workspace.setOrientation(orient)
        if drag_widget is drop_widget:
            drop_widget = drag_widget.copy()
        widgets = [drop_widget, drag_widget]
        widgets = widgets if is_after else reversed(widgets)
        for widget in widgets:
            super(MWorkspace, workspace).addWidget(widget)

        super(MWorkspace, drop_parent).insertWidget(max(0, drop_id), workspace)

    def _create_tab_widget(self, widget, title="", source=None):
        tab_widget = source.copy() if source else MWorkspaceTabWidget()
        tab_widget.setProperty("renameable", self.property("renameable"))
        tab_widget.setProperty("showBarOverlay", self.property("showBarOverlay"))
        tab_widget.setProperty(
            "autoHideBarOverlay", self.property("autoHideBarOverlay")
        )

        tab_widget.sig_border_drop.connect(self.slot_border_drop)
        title = title or widget.windowTitle() or self.DEFAULT_TAB_TITLE
        tab_widget.addTab(widget, title)
        return tab_widget

    def insertWidget(self, index, widget, title=""):
        tab_widget = self._create_tab_widget(widget, title)
        super(MWorkspace, self).insertWidget(index, tab_widget)

    def addWidget(self, widget, title=""):
        tab_widget = self._create_tab_widget(widget, title)
        super(MWorkspace, self).addWidget(tab_widget)

    def addTab(self, workspace_id, widget, *args):
        tab_widget = super(MWorkspace, self).widget(workspace_id)
        args = args if args else (widget.windowTitle() or self.DEFAULT_TAB_TITLE,)
        tab_widget.addTab(widget, *args)

    def insertTab(self, workspace_id, index, widget, *args):
        tab_widget = super(MWorkspace, self).widget(workspace_id)
        args = args if args else (widget.windowTitle() or self.DEFAULT_TAB_TITLE,)
        tab_widget.addTab(index, widget, *args)

    def widget(self, index):
        widget = super(MWorkspace, self).widget(index)
        if not widget:
            raise ValueError("invalid widget index")
        return widget
