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
from six.moves import cPickle

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.mixin import cursor_mixin
from dayu_widgets.mixin import property_mixin
from dayu_widgets.mixin import stacked_animation_mixin


@cursor_mixin
class MTabBar(QtWidgets.QTabBar):

    sig_start_drag = QtCore.Signal(int)
    sig_bar_press = QtCore.Signal(QtWidgets.QTabBar)
    sig_bar_menu = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(MTabBar, self).__init__(parent)
        self.dragging = False

        # self.setAcceptDrops(True)

        self.setDrawBase(False)
        self.setMovable(True)
        self.setMouseTracking(True)

    def tabSizeHint(self, index):
        tab_text = self.tabText(index)
        if self.tabsClosable():
            return QtCore.QSize(
                self.fontMetrics().width(tab_text) + 70,
                self.fontMetrics().height() + 20,
            )
        else:
            return QtCore.QSize(
                self.fontMetrics().width(tab_text) + 50,
                self.fontMetrics().height() + 20,
            )

    def mousePressEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMousePressEvent) -> None
        super(MTabBar, self).mousePressEvent(event)
        if event.buttons() == QtCore.Qt.LeftButton:
            self.dragging = True
            self.sig_bar_press.emit(self)

    def mouseMoveEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMouseMoveEvent) -> None
        super(MTabBar, self).mouseMoveEvent(event)
        index = self.currentIndex()
        condition = self.dragging
        condition &= event.buttons() == QtCore.Qt.LeftButton
        condition &= bool(self.count())
        condition &= index != -1
        # NOTES(timmyliang): trigger when it drag out of tabbar
        condition &= not self.rect().contains(event.pos())

        if condition:
            self.sig_start_drag.emit(index)

    def mouseReleaseEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QMouseReleaseEvent) -> None
        super(MTabBar, self).mouseReleaseEvent(event)
        if self.dragging and event.buttons() == QtCore.Qt.LeftButton:
            self.dragging = False

    def focusOutEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QFocusOutEvent) -> None
        super(MTabBar, self).focusOutEvent(event)
        if self.dragging:
            self.dragging = False

    def contextMenuEvent(self, event):
        # type: (QtWidgets.QTabBar,QtGui.QContextMenuEvent) -> None
        super(MTabBar, self).contextMenuEvent(event)
        index = self.tabAt(event.pos())
        self.sig_tab_menu.emit(index)


class MTabOverlay(QtWidgets.QWidget):

    sig_painted = QtCore.Signal(QtGui.QPainter)

    def __init__(self, parent):
        super(MTabOverlay, self).__init__(parent)
        self.tab = parent
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        flags = QtCore.Qt.WindowTransparentForInput | QtCore.Qt.FramelessWindowHint
        self.setWindowFlags(flags)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if not obj.isWidgetType():
            return False

        if event.type() & (QtCore.QEvent.Resize | QtCore.QEvent.Show):
            self.setGeometry(obj.rect())

        return False

    def paintEvent(self, event):

        painter = QtGui.QPainter(self)
        self.sig_painted.emit(painter)
        super(MTabOverlay, self).paintEvent(event)


@property_mixin
@stacked_animation_mixin
class MTabWidget(QtWidgets.QTabWidget):
    sig_tab_drag = QtCore.Signal(QtWidgets.QWidget)
    MINE = "application/dayu_tab_data"

    def __init__(self, parent=None):
        super(MTabWidget, self).__init__(parent=parent)

        self.bar = MTabBar(self)
        self.setTabBar(self.bar)
        self.bar.sig_start_drag.connect(self.slot_drag_tab)
        self.bar.sig_bar_press.connect(self.slot_bar_press)
        self.bar.sig_bar_menu.connect(lambda i: print("asd"))

        self.overlay = MTabOverlay(self)
        self.overlay.sig_painted.connect(self.slot_painted)

        # TODO(timmyliang) add MSplitter for resize

        self.setAcceptDrops(True)
        self.setProperty("draggable", True)
        self.is_new_window = True
        self.is_dragging = False

    @property
    def is_dragging(self):
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value):
        self.overlay.setVisible(value)
        self._is_dragging = value

    def copy(self, parent=None):
        parent = parent or self
        widget = MTabWidget(parent)

        meta = parent.metaObject()
        props = [bytes(p).decode("utf-8") for p in parent.dynamicPropertyNames()]
        props += [meta.property(i).name() for i in range(meta.propertyCount())]

        for prop_name in props:
            if prop_name.startswith("_"):
                continue
            val = parent.property(prop_name)
            if val is not None:
                widget.setProperty(prop_name, val)

        return widget

    def slot_drag_tab(self, index):
        # type: (QtWidgets.QTabWidget,int) -> None
        drag = QtGui.QDrag(self)
        data = QtCore.QMimeData(self)

        # TODO Drag data
        # widget = self.widget(index)
        buff = cPickle.dumps(index)
        data.setData(self.MINE, QtCore.QByteArray(buff))
        drag.setMimeData(data)

        # NOTES(timmyliang): create drag pixmap
        bar_pixmap = self.bar_pixmap

        rect = self.rect()
        rect -= QtCore.QMargins(0, self.bar.height(), rect.width(), rect.height())
        widget_pixmap = self.grab(rect)

        w = widget_pixmap.width()
        h = bar_pixmap.height() + widget_pixmap.height()
        pixmap = QtGui.QPixmap(w, h)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.drawPixmap(QtCore.QPoint(), bar_pixmap)
        painter.drawPixmap(QtCore.QPoint(0, bar_pixmap.height()), widget_pixmap)
        painter.end()

        drag.setPixmap(pixmap)
        drag.destroyed.connect(partial(self.slot_drag_destroyed, index))
        drag.start(QtCore.Qt.MoveAction)

    def slot_bar_press(self, bar):
        self.bar_pixmap = bar.grab(bar.tabRect(bar.currentIndex()))

    def slot_drag_destroyed(self, index):

        if not self.is_new_window:
            self.is_new_window = True
            return

        widget = self.widget(index)
        label = self.tabText(index)
        tab = self.copy()
        tab.setWindowFlags(QtCore.Qt.Window)
        tab.addTab(widget, label)
        tab.show()
        tab.move(QtGui.QCursor.pos())
        tab.raise_()
        tab.setFocus()

        if not self.count():
            self.close()

    def slot_painted(self, painter):

        rect = self.rect()

        height = 10
        top_left = rect.topLeft()
        bottom_right = QtCore.QPoint(rect.topRight().x(), height)
        # top_left = rect.bottomLeft() + QtCore.QPoint(0,height)
        # bottom_right = rect.bottomRight()
        color = QtGui.QColor(dayu_theme.blue)
        painter.fillRect(QtCore.QRect(top_left, bottom_right), color)

    def _get_drag_data(self, event):
        data = event.mimeData()
        buff = data.data(self.MINE)
        if not buff:
            return event.ignore()
        return buff

    def dragEnterEvent(self, event):
        super(MTabWidget, self).dragEnterEvent(event)
        self.is_dragging = True
        if self._get_drag_data(event):
            event.accept()

    def dragMoveEvent(self, event):
        super(MTabWidget, self).dragMoveEvent(event)
        buff = self._get_drag_data(event)

        # TODO draw position calc
        self.overlay.repaint()

        event.accept()

    def dropEvent(self, event):
        self.is_dragging = False
        buff = self._get_drag_data(event)
        index = cPickle.loads(buff)
        source = event.source()
        assert isinstance(source, MTabWidget), "unknown drop error"

        source.is_new_window = False
        label = source.tabText(index)
        widget = source.widget(index)

        # TODO add tab base on position index
        self.addTab(widget, label)

        if not source.count():
            source.close()

    def dragLeaveEvent(self, event):
        self.is_dragging = False
        event.accept()
