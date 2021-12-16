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
from collections import OrderedDict
from collections import defaultdict
from collections import namedtuple
from functools import partial

# Import third-party modules
from Qt import QtCore
from Qt import QtGui
from Qt import QtWidgets
from Qt.QtCompat import isValid
import six
from six.moves import cPickle

# Import local modules
from dayu_widgets import dayu_theme
from dayu_widgets.mixin import cursor_mixin
from dayu_widgets.mixin import property_mixin
from dayu_widgets.mixin import stacked_animation_mixin
from dayu_widgets.push_button import MPushButton
from dayu_widgets.qt import defer
from dayu_widgets.splitter import MSplitter
from dayu_widgets.text_edit import MTextEdit


@cursor_mixin
class MTabBar(QtWidgets.QTabBar):

    sig_start_drag = QtCore.Signal(int)
    sig_bar_press = QtCore.Signal(QtWidgets.QTabBar)
    sig_bar_menu = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(MTabBar, self).__init__(parent)
        self.dragging = False

        # self.setAcceptDrops(True)
        self.setProperty("draggable", True)
        self.setDrawBase(False)
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
        condition &= bool(self.property("draggable"))

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
        self.sig_bar_menu.emit(index)


class MTabOverlay(QtWidgets.QWidget):

    sig_painted = QtCore.Signal(QtGui.QPainter)

    def __init__(self, parent):
        super(MTabOverlay, self).__init__(parent)
        self.tab = parent
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        parent.installEventFilter(self)

        self.button = MPushButton()
        self.button.setText(self.tr("Remove"))
        self.button.clicked.connect(parent.deleteLater)
        self.button.setVisible(False)
        parent.installEventFilter(self)

        layout = QtWidgets.QVBoxLayout()
        inside_layout = QtWidgets.QHBoxLayout()
        inside_layout.addStretch()
        inside_layout.addWidget(self.button)
        inside_layout.addStretch()
        layout.addLayout(inside_layout)
        self.setLayout(layout)

    def eventFilter(self, obj, event):
        if event.type() & (QtCore.QEvent.Resize | QtCore.QEvent.Show):
            self.setGeometry(obj.rect())
        return False

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        self.sig_painted.emit(painter)
        super(MTabOverlay, self).paintEvent(event)


class SplitterRemoveFilter(QtCore.QObject):
    def __init__(self, parent):
        super(SplitterRemoveFilter, self).__init__(parent)
        self.target = parent
        parent.destroyed.connect(self.deleteLater)
        parent.installEventFilter(self)

    def eventFilter(self, receiver, event):
        typ = event.type()
        if typ in [QtCore.QEvent.ChildRemoved]:
            if isValid(self.target) and not self.target.count():
                parent = self.target.parent()
                if isinstance(parent, MTabWidget) and not parent.count():
                    parent.setParent(None)
                else:
                    self.target.setParent(None)

        return super(SplitterRemoveFilter, self).eventFilter(receiver, event)


# def draggable(flag):
#     def decorator(func):
#         def wrapper(self, *args, **kwargs):
#             if self.property("draggable") == flag:
#                 return func(self, *args, **kwargs)

#         return wrapper

#     return decorator


@property_mixin
@stacked_animation_mixin
class MTabWidget(QtWidgets.QTabWidget):

    DIRECTIONS = "E S W N"
    DIRECTION = namedtuple("Direction", DIRECTIONS)(0, 1, 2, 3)
    sig_tab_drag = QtCore.Signal(QtWidgets.QWidget)
    sig_tab_drop = QtCore.Signal(int)
    sig_border_drop = QtCore.Signal(QtWidgets.QWidget, int, int)
    MINE = "application/dayu_tab_data"

    def __init__(self, parent=None):
        super(MTabWidget, self).__init__(parent=parent)

        self.signal_list = []
        self.method_list = []
        meta = self.metaObject()
        for i in range(meta.methodCount()):
            method = meta.method(i)
            method_name = method.name()
            self.method_list.append(method_name)
            if method.methodType() == QtCore.QMetaMethod.Signal:
                self.signal_list.append(method_name)

        self.bar = MTabBar(self)
        self.setTabBar(self.bar)
        self.bar.sig_start_drag.connect(self.slot_drag_tab)
        self.bar.sig_bar_press.connect(self.slot_bar_press)
        self.bar.sig_bar_menu.connect(lambda i: print("asd"))

        self.overlay = MTabOverlay(self)
        self.overlay.sig_painted.connect(self.slot_painted)

        self.sig_border_drop.connect(self.slot_border_drop)

        self.setMovable(True)
        self.setProperty("hint_size", 5)
        self.setProperty("draggable", False)
        self.setProperty("hint_opacity", 0.5)
        self.setProperty("hint_color", dayu_theme.blue)

        self.is_in_container = False
        self.is_new_window = True
        self.is_dragging = False
        self.on_border_index = -1
        self.on_tab_index = -1
        self.rect_data = defaultdict(dict)

        self._validate_tab_count()

    def _set_draggable(self, value):
        self.setAcceptDrops(value)
        self.bar.setProperty("draggable", value)

    @property
    def is_dragging(self):
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value):
        self.overlay.setVisible(value)
        self._is_dragging = value

    def slot_drag_tab(self, index):
        # type: (QtWidgets.QTabWidget,int) -> None
        drag = QtGui.QDrag(self)
        data = QtCore.QMimeData(self)

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
        drag.destroyed.connect(partial(self.slot_dropped_outside, index))
        drag.start(QtCore.Qt.MoveAction)

    def slot_bar_press(self, bar):
        self.bar_pixmap = bar.grab(bar.tabRect(bar.currentIndex()))

    def slot_dropped_outside(self, index):

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

    def slot_painted(self, painter):
        if not self.count() and not self.is_dragging:
            painter.fillRect(self.rect(), QtCore.Qt.transparent)
            return

        pos = QtGui.QCursor.pos()
        pos = self.mapFromGlobal(pos)

        color = QtGui.QColor(self.property("hint_color"))
        painter.setOpacity(self.property("hint_opacity"))

        rect = self.rect()

        self.on_border_index = -1
        self.on_tab_index = -1

        for index, rect in enumerate(self.rect_data.get("border", [])):
            if rect.contains(pos):
                self.on_border_index = index
                break
        else:

            rect_tab = self.rect_data.get("rect_tab", {})
            for index, (_rect, rect) in enumerate(rect_tab.items()):
                if _rect.contains(pos):
                    self.on_tab_index = index
                    break

            rect_widget = self.rect_data["rect_widget"]
            if isinstance(rect_widget, QtCore.QRect):
                painter.fillRect(rect_widget, color)

        painter.fillRect(rect, color)

    def slot_border_drop(self, source, index, direction):

        expanding = QtWidgets.QSizePolicy.Expanding
        self.setSizePolicy(expanding, expanding)
        self.setMinimumHeight(150)
        self.is_in_container = False

        orient = QtCore.Qt.Vertical if direction in [1, 3] else QtCore.Qt.Horizontal
        is_after = direction in [2, 3]

        parent = self.parent()
        label = source.tabText(index)
        widget = source.widget(index)
        if not widget or not label:
            return
        inst = self.copy()
        inst.is_in_container = True
        inst.addTab(widget, label)
        if isinstance(parent, QtWidgets.QSplitter):
            self.splitter = parent
            if orient == self.splitter.orientation():
                splitter_index = self.splitter.indexOf(self)
                splitter_index = splitter_index if is_after else splitter_index + 1
                self.splitter.insertWidget(splitter_index, inst)
                return

        this = self.copy(True)
        this.is_in_container = True

        self.splitter = QtWidgets.QSplitter()
        SplitterRemoveFilter(self.splitter)
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.splitter)
        self.setLayout(layout)
        widget_list = [inst, this] if is_after else [this, inst]
        for w in widget_list:
            self.splitter.addWidget(w)

        self.splitter.setOrientation(orient)

    def dragEnterEvent(self, event):
        super(MTabWidget, self).dragEnterEvent(event)
        self.is_dragging = True
        if self._get_drag_data(event):
            rect = self.rect()
            size = self.property("hint_size")
            tl = rect.topLeft()
            br = rect.topRight() + QtCore.QPoint(0, size)
            rect_N = QtCore.QRect(tl, br)
            tl = rect.topRight() - QtCore.QPoint(size, 0)
            br = rect.bottomRight()
            rect_E = QtCore.QRect(tl, br)
            tl = rect.bottomLeft() - QtCore.QPoint(0, size)
            br = rect.bottomRight()
            rect_S = QtCore.QRect(tl, br)
            tl = rect.topLeft()
            br = rect.bottomLeft() + QtCore.QPoint(size, 0)
            rect_W = QtCore.QRect(tl, br)

            self.rect_data["border"] = [rect_E, rect_S, rect_W, rect_N]
            tab_rect = rect_W
            rect_tab = OrderedDict()
            for i in range(self.bar.count()):
                tab_rect = self.bar.tabRect(i)
                tl = tab_rect.topLeft()
                br = QtCore.QPoint(tab_rect.bottomRight().x(), rect.bottomRight().y())
                rect_tab[QtCore.QRect(tl, br)] = tab_rect

            tl = rect.topLeft()
            br = rect.bottomRight()
            rect_widget = QtCore.QRect(tl + QtCore.QPoint(0, tab_rect.height()), br)
            self.rect_data["rect_widget"] = rect_widget

            # NOTES(timmyliang): left area
            tl = tab_rect.topRight()
            br = rect.bottomRight()
            rect = QtCore.QRect(tl, QtCore.QPoint(br.x(), tab_rect.bottomRight().y()))
            rect_tab[QtCore.QRect(tl, br)] = rect
            self.rect_data["rect_tab"] = rect_tab

            event.accept()

    def dragMoveEvent(self, event):
        super(MTabWidget, self).dragMoveEvent(event)
        if self._get_drag_data(event):
            self.overlay.repaint()
            event.accept()

    def dropEvent(self, event):
        super(MTabWidget, self).dropEvent(event)

        self.is_dragging = False
        buff = self._get_drag_data(event)
        index = cPickle.loads(buff)
        source = event.source()
        assert isinstance(source, MTabWidget), "unknown drop error"

        source.is_new_window = False
        label = source.tabText(index)
        widget = source.widget(index)

        if self.on_tab_index >= 0:
            self.insertTab(self.on_tab_index, widget, label)
            self.setCurrentIndex(self.on_tab_index)
            self.sig_tab_drop.emit(self.on_tab_index)
        elif self.on_border_index >= 0:
            self.sig_border_drop.emit(source, index, self.on_border_index)
        self._validate_tab_count()

    def dragLeaveEvent(self, event):
        super(MTabWidget, self).dragLeaveEvent(event)
        self.is_dragging = False
        if not self.count():
            self.overlay.setVisible(True)
        event.accept()

    def tabRemoved(self, *args):
        self._validate_tab_count()
        return super(MTabWidget, self).tabRemoved(*args)

    @defer
    def _validate_tab_count(self):
        count = self.count()
        is_window = self.windowFlags() & QtCore.Qt.Window
        if not count and is_window:
            self.close()
        if self.property("draggable"):
            self.overlay.repaint()
            self.overlay.setVisible(not count)
            self.overlay.button.setVisible(not count)

            # if count == 1:
            #     self.bar.setVisible(False)
            # elif not self.bar.isVisible():
            #     self.bar.setVisible(True)

    def _get_drag_data(self, event):
        data = event.mimeData()
        buff = data.data(self.MINE)
        if not buff:
            return event.ignore()
        return buff

    def copy(self, tab=False):
        inst = MTabWidget(self.window())
        meta = self.metaObject()
        props = [bytes(p).decode("utf-8") for p in self.dynamicPropertyNames()]
        props += [meta.property(i).name() for i in range(meta.propertyCount())]
        props.remove("objectName")

        for prop_name in props:
            if prop_name.startswith("_"):
                continue
            val = self.property(prop_name)
            if val is not None:
                inst.setProperty(prop_name, val)

        if tab:
            for index in range(self.count())[::-1]:
                widget = self.widget(index)
                label = self.tabText(index)
                inst.addTab(widget, label)

            # NOTES(timmyliang): singal connections
            for signal_name in self.signal_list:
                signal_name = bytes(signal_name).decode("utf-8")
                src_signal = getattr(self, signal_name)
                dst_signal = getattr(inst, signal_name)
                dst_signal.connect(src_signal.emit)

            self.setProperty("draggable", False)
            # # TODO all method to inst
            # for index,(name,member) in enumerate(inspect.getmembers(self,inspect.isroutine)):
            #     if name.startswith("_") or index > 100:
            #         continue
            #     if "event" in name.lower():
            #         continue
            #     print(name)
            #     setattr(self, name,getattr(inst, name))

            # TODO(timmyliang): specific method replace works
            for name in ["tabText", "removeTab"]:
                setattr(self, name, getattr(inst, name))

            # for n,m in inst.__dict__.items():
            #     self.__dict__[n] = m

        return inst
