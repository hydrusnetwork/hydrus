# QLocator
# Copyright (C) 2020-2022 qcomixdev

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
import random
import math
import re

def elideRichText(richText: str, maxWidth: int, widget, elideFromLeft: bool):
    doc = QG.QTextDocument()
    opt = QG.QTextOption()
    opt.setWrapMode(QG.QTextOption.NoWrap)
    doc.setDefaultTextOption(opt)
    doc.setDocumentMargin(0)
    doc.setHtml(richText)
    doc.adjustSize()

    if doc.size().width() > maxWidth:
        cursor = QG.QTextCursor (doc)
        if elideFromLeft:
            cursor.movePosition(QG.QTextCursor.Start)
        else:
            cursor.movePosition(QG.QTextCursor.End)
        elidedPostfix = "…"
        metric = QG.QFontMetrics(widget.font())
        postfixWidth = metric.horizontalAdvance(elidedPostfix)

        while doc.size().width() > maxWidth - postfixWidth:
            if elideFromLeft:
                cursor.deleteChar()
            else:
                cursor.deletePreviousChar()
            doc.adjustSize()

        cursor.insertText(elidedPostfix)

        return doc.toHtml()

    return richText

class FocusEventFilter(QC.QObject):
    focused = QC.Signal()
    def __init__(self, parent = None):
        super().__init__(parent)

    def eventFilter(self, watched, event) -> bool:
        try:
            
            if event.type() == QC.QEvent.FocusIn:
                
                self.focused.emit()
                
            
        except Exception as e:
            
            return True
            
        
        return False

class QLocatorSearchResult:
    def __init__(self, id: int, defaultIconPath: str, selectedIconPath: str, closeOnActivated: bool, text: list, toggled: bool = False, toggledIconPath: str = "", toggledSelectedIconPath: str = ""):
        self.id = id
        self.defaultIconPath = defaultIconPath
        self.selectedIconPath = selectedIconPath
        self.closeOnActivated = closeOnActivated
        self.text = text
        self.toggled = toggled
        self.toggledIconPath = toggledIconPath
        self.toggledSelectedIconPath = toggledSelectedIconPath

class QLocatorTitleWidget(QW.QWidget):
    def __init__(self, title: str, iconPath: str, height: int, shouldRemainHidden: bool, parent = None):
        super().__init__(parent)
        self.icon = QG.QIcon(iconPath)
        self.iconHeight = height - 2
        self.setLayout(QW.QHBoxLayout())
        self.iconLabel = QW.QLabel()
        self.iconLabel.setFixedHeight(self.iconHeight)
        self.iconLabel.setPixmap(self.icon.pixmap(self.iconHeight, self.iconHeight))
        self.titleLabel = QW.QLabel()
        self.titleLabel.setText(title)
        self.titleLabel.setTextFormat(QC.Qt.RichText)
        self.countLabel = QW.QLabel()
        self.layout().setContentsMargins(4, 1, 4, 1)
        self.layout().addWidget(self.iconLabel)
        self.layout().addWidget(self.titleLabel)
        self.layout().addStretch(1)
        self.layout().addWidget(self.countLabel)
        self.layout().setAlignment(self.countLabel, QC.Qt.AlignVCenter)
        self.layout().setAlignment(self.iconLabel, QC.Qt.AlignVCenter)
        self.layout().setAlignment(self.titleLabel, QC.Qt.AlignVCenter)
        titleFont = self.titleLabel.font()
        titleFont.setBold(True)
        self.titleLabel.setFont(titleFont)
        self.setFixedHeight(height)
        self.shouldRemainHidden = shouldRemainHidden

    def updateData(self, count: int):
        self.countLabel.setText(str(count))

    def paintEvent(self, event):
        opt = QW.QStyleOption()
        opt.initFrom(self)
        p = QG.QPainter(self)
        self.style().drawPrimitive(QW.QStyle.PE_Widget, opt, p, self)

class QLocatorResultWidget(QW.QWidget):
    up = QC.Signal()
    down = QC.Signal()
    activated = QC.Signal(int, int, bool)
    entered = QC.Signal()
    def __init__(self, keyEventTarget: QW.QWidget, height: int, primaryTextWidth: int, secondaryTextWidth: int, parent = None):
        super().__init__(parent)
        self.iconHeight = height - 2
        self.setObjectName("unselectedLocatorResult")
        self.keyEventTarget = keyEventTarget
        self.setLayout(QW.QHBoxLayout())
        self.iconLabel = QW.QLabel(self)
        self.iconLabel.setFixedHeight(self.iconHeight)
        self.mainTextLabel = QW.QLabel(self)
        self.primaryTextWidth = primaryTextWidth
        self.mainTextLabel.setMinimumWidth(primaryTextWidth)
        self.mainTextLabel.setTextFormat(QC.Qt.RichText)
        self.mainTextLabel.setTextInteractionFlags(QC.Qt.NoTextInteraction)
        self.secondaryTextLabel = QW.QLabel(self)
        self.secondaryTextWidth = secondaryTextWidth
        self.secondaryTextLabel.setMaximumWidth(secondaryTextWidth)
        self.secondaryTextLabel.setTextFormat(QC.Qt.RichText)
        self.secondaryTextLabel.setTextInteractionFlags(QC.Qt.NoTextInteraction)
        self.layout().setContentsMargins(4, 1, 4, 1)
        self.layout().addWidget(self.iconLabel)
        self.layout().addWidget(self.mainTextLabel)
        self.layout().addStretch(1)
        self.layout().addWidget(self.secondaryTextLabel)
        self.layout().setAlignment(self.mainTextLabel, QC.Qt.AlignVCenter)
        self.layout().setAlignment(self.iconLabel, QC.Qt.AlignVCenter)
        self.layout().setAlignment(self.secondaryTextLabel, QC.Qt.AlignVCenter)
        self.setFixedHeight(height)
        self.setSizePolicy(QW.QSizePolicy.Expanding, QW.QSizePolicy.Fixed)
        self.activateEnterShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key_Enter), self)
        self.activateEnterShortcut.setContext(QC.Qt.WidgetShortcut)
        self.activateReturnShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key_Return), self)
        self.activateReturnShortcut.setContext(QC.Qt.WidgetShortcut)
        self.upShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key_Up), self)
        self.upShortcut.setContext(QC.Qt.WidgetShortcut)
        self.downShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key_Down), self)
        self.downShortcut.setContext(QC.Qt.WidgetShortcut)

        self.selectedPalette = self.palette()
        self.selectedPalette.setColor(QG.QPalette.Window, QG.QPalette().color(QG.QPalette.WindowText))
        self.selectedPalette.setColor(QG.QPalette.WindowText, QG.QPalette().color(QG.QPalette.Window))

        self.id = -1
        self.providerIndex = -1
        self.closeOnActivated = False
        self.selected = False
        self.defaultStylingEnabled = True
        self.currentIcon = QG.QIcon()
        self.currentToggledIcon = QG.QIcon()
        self.toggled = False

        self.activateEnterShortcut.activated.connect(self.activate)
        self.activateReturnShortcut.activated.connect(self.activate)

        self.upShortcut.activated.connect(self.up)
        self.downShortcut.activated.connect(self.down)

    def paintEvent(self, event):
        opt = QW.QStyleOption()
        opt.initFrom(self)
        p = QG.QPainter(self)
        self.style().drawPrimitive(QW.QStyle.PE_Widget, opt, p, self)

    def enterEvent(self, event):
        self.entered.emit()

    def mousePressEvent(self, event):
        self.entered.emit()

    def mouseReleaseEvent(self, event):
        self.activate()

    def activate(self):
        if not self.closeOnActivated:
            self.toggled = not self.toggled
            iconToUse = self.currentIcon if not self.toggled else self.currentToggledIcon
            self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Selected if self.selected else QG.QIcon.Normal))
        self.activated.emit(self.providerIndex, self.id, self.closeOnActivated)

    def updateData(self, providerIndex: int, data: QLocatorSearchResult):
        self.toggled = data.toggled
        self.currentIcon = QG.QIcon()
        self.currentIcon.addFile(data.defaultIconPath, QC.QSize(), QG.QIcon.Normal)
        self.currentIcon.addFile(data.selectedIconPath, QC.QSize(), QG.QIcon.Selected)
        self.currentToggledIcon = QG.QIcon()
        self.currentToggledIcon.addFile(data.toggledIconPath, QC.QSize(), QG.QIcon.Normal)
        self.currentToggledIcon.addFile(data.toggledSelectedIconPath, QC.QSize(), QG.QIcon.Selected)
        iconToUse = self.currentIcon if not self.toggled else self.currentToggledIcon
        self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Selected if self.selected else QG.QIcon.Normal))
        self.mainTextLabel.clear()
        self.secondaryTextLabel.clear()
        if len(data.text) > 0:
            self.mainTextLabel.setText(elideRichText(data.text[0], self.primaryTextWidth, self.mainTextLabel, False))
        if len(data.text) > 1:
            self.secondaryTextLabel.setText(elideRichText(data.text[1], self.secondaryTextWidth, self.secondaryTextLabel, True))
        self.id = data.id
        self.closeOnActivated = data.closeOnActivated
        self.providerIndex = providerIndex

    def setDefaultStylingEnabled(self, enabled: bool):
        if self.defaultStylingEnabled and not enabled: self.setPalette(QG.QPalette())
        self.defaultStylingEnabled = enabled

    def setSelected(self, selected: bool):
        self.selected = selected
        if selected:
            self.setObjectName("selectedLocatorResult")
            if self.defaultStylingEnabled: self.setPalette(self.selectedPalette)
            self.style().unpolish(self)
            self.style().polish(self)
            self.setFocus()
        else:
            self.setObjectName("unselectedLocatorResult")
            if self.defaultStylingEnabled: self.setPalette(QG.QPalette())
            self.style().unpolish(self)
            self.style().polish(self)
        iconToUse = self.currentIcon if not self.toggled else self.currentToggledIcon
        self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Selected if self.selected else QG.QIcon.Normal))

    def keyPressEvent(self, ev: QG.QKeyEvent):
        if ev.key() != QC.Qt.Key_Up and ev.key() != QC.Qt.Key_Down and ev.key() != QC.Qt.Key_Enter and ev.key() != QC.Qt.Key_Return:
            QW.QApplication.postEvent(self.keyEventTarget, QG.QKeyEvent(ev.type(), ev.key(), ev.modifiers(), ev.text(), ev.isAutoRepeat()))
            self.keyEventTarget.setFocus()
        else:
            super().keyPressEvent(self, ev)

class QAbstractLocatorSearchProvider(QC.QObject):
    resultsAvailable = QC.Signal(int, list)
    def __init__(self, parent = None):
        super().__init__(parent)

class QExampleSearchProvider(QAbstractLocatorSearchProvider):
    def __init__(self, parent = None):
        super().__init__(parent)

    def title(self):
        return "Example search provider"

    def suggestedReservedItemCount(self):
        return 32

    def resultSelected(self, resultID: int):
        pass

    def processQuery(self, query: str, context, jobID: int):
        resCount = random.randint(0, 50)
        results = []
        for i in range(resCount):
            randomStr = str()
            for j in range(5):
                randomStr += str(chr(97+random.randint(0, 26)))
            txt = []
            txt.append("Result <b>text</b> #" + str(i) + randomStr)
            txt.append("Secondary result text")
            results.append(QLocatorSearchResult(0, "icon.svg", "icon.svg", True, txt, False, "icon.svg", "icon.svg"))
        self.resultsAvailable.emit(jobID, results)

    def stopJobs(self, jobs):
        pass

    def hideTitle(self):
        return False

    def titleIconPath(self):
        return "icon.svg"

class QCalculatorSearchProvider(QAbstractLocatorSearchProvider):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.safeEnv = {
            'ceil': math.ceil,
            'abs': abs,
            'floor': math.floor,
            'gcd': math.gcd,
            'exp': math.exp,
            'log': math.log,
            'log2': math.log2,
            'log10': math.log10,
            'pow': math.pow,
            'sqrt': math.sqrt,
            'acos': math.acos,
            'asin': math.asin,
            'atan': math.atan,
            'atan2': math.atan2,
            'cos': math.cos,
            'hypot': math.hypot,
            'sin': math.sin,
            'tan': math.tan,
            'degrees': math.degrees,
            'radians': math.radians,
            'acosh': math.acosh,
            'asinh': math.asinh,
            'atanh': math.atanh,
            'cosh': math.cosh,
            'sinh': math.sinh,
            'tanh': math.tanh,
            'erf': math.erf,
            'erfc': math.erfc,
            'gamma': math.gamma,
            'lgamma': math.lgamma,
            'pi': math.pi,
            'e': math.e,
            'inf': math.inf,
            'randint': random.randint,
            'random': random.random,
            'factorial': math.factorial
        }
        self.safePattern = re.compile("^("+"|".join(self.safeEnv.keys())+r"|[0-9.*+\-%/()]|\s" + ")+$")

    def processQuery(self, query: str, context, jobID: int):
        try:
            if len(query.strip()) and self.safePattern.match(query):
                result = str(eval(query, {"__builtins__": {}}, self.safeEnv))
                try:
                    int(result)
                except:
                    result = str(float(result))
                self.resultsAvailable.emit(jobID, [QLocatorSearchResult(0, self.iconPath(), self.selectedIconPath(), False, [result,"Calculator"], False, self.iconPath(), self.selectedIconPath())])
        except:
            pass

    def title(self):
        return str()

    def suggestedReservedItemCount(self):
        return 1

    def resultSelected(self, resultID: int):
        pass

    def stopJobs(self, jobs):
        pass

    def hideTitle(self):
        return True

    def titleIconPath(self):
        return str()

    def selectedIconPath(self):
        return str()

    def iconPath(self):
        return str()

class QLocatorWidget(QW.QWidget):
    finished = QC.Signal()
    def __init__(self, parent = None, width: int = 600, resultHeight: int = 36, titleHeight: int = 36, primaryTextWidth: int = 320, secondaryTextWidth: int = 200, maxVisibleItemCount: int = 8):
        super().__init__(parent)
        self.alignment = QC.Qt.AlignCenter
        self.resultHeight = resultHeight
        self.titleHeight = titleHeight
        self.primaryTextWidth = primaryTextWidth
        self.locator = None
        self.secondaryTextWidth = secondaryTextWidth
        self.maxVisibleItemCount = maxVisibleItemCount
        self.reservedItemCounts = []
        self.visibleResultItemCounts = []
        self.currentJobIds = []
        self.titleItems = []
        self.resultItems = []
        self.escapeShortcuts = []
        self.selectedLayoutItemIndex = 0
        self.defaultStylingEnabled = True
        self.context = None
        self.lastQuery = str()
        self.setVisible(False)
        self.setLayout(QW.QVBoxLayout())
        self.searchEdit = QW.QLineEdit()
        self.resultList = QW.QScrollArea()
        self.resultLayout = QW.QVBoxLayout()
        self.resultList.setWidget(QW.QWidget())
        self.resultList.widget().setLayout(self.resultLayout)
        self.resultList.setWidgetResizable(True)
        self.resultLayout.setSizeConstraint(QW.QLayout.SetMinAndMaxSize)
        self.layout().addWidget(self.searchEdit)
        self.layout().addWidget(self.resultList)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.resultLayout.setContentsMargins(0, 0, 0, 0)
        self.resultLayout.setSpacing(0)
        self.setFixedWidth(width)
        self.setWindowFlags(QC.Qt.FramelessWindowHint | QC.Qt.WindowStaysOnTopHint | QC.Qt.CustomizeWindowHint | QC.Qt.Popup)
        self.resultList.setSizeAdjustPolicy(QW.QAbstractScrollArea.AdjustToContents)
        self.setSizePolicy(QW.QSizePolicy.Fixed, QW.QSizePolicy.Maximum)
        self.setEscapeShortcuts([QC.Qt.Key_Escape])
        self.editorDownShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key_Down), self.searchEdit)
        self.editorDownShortcut.setContext(QC.Qt.WidgetShortcut)
        self.editorDownShortcut.activated.connect(self.handleEditorDown)

        def handleTextEdited():
            for i in range(len(self.resultItems)):
                for it in self.resultItems[i]: self.setResultVisible(it, False)
                self.setResultVisible(self.titleItems[i], False)
            self.selectedLayoutItemIndex = 0
            self.updateResultListHeight()
        self.searchEdit.textEdited.connect(handleTextEdited)

        def handleSearchFocused():
            if self.selectedLayoutItemIndex < self.resultLayout.count():
                widget = self.resultLayout.itemAt(self.selectedLayoutItemIndex).widget()
                if widget:
                    if isinstance(widget, QLocatorResultWidget):
                        widget.setSelected(False)
                        self.selectedLayoutItemIndex = 0
        filter = FocusEventFilter()
        self.searchEdit.installEventFilter(filter)
        filter.focused.connect(handleSearchFocused)

        self.queryTimer = QC.QTimer(self)
        self.queryTimer.setInterval(0)
        self.queryTimer.setSingleShot(True)

        def handleQueryTimeout():
            if not self.locator: return
            self.currentJobIds = self.locator.query(self.lastQuery, self.context)
        self.queryTimer.timeout.connect(handleQueryTimeout)
        self.searchEdit.textEdited.connect(self.queryLocator)

        self.updateResultListHeight()

    def setAlignment( self, alignment ):
        if alignment == QC.Qt.AlignCenter:
            self.alignment = alignment
            self.updateAlignment()
        elif alignment == QC.Qt.AlignTop:
            self.alignment = alignment
            self.updateAlignment()

    def updateAlignment( self ):
        widget = self
        while True:
            parent = widget.parentWidget()
            if not parent:
                break
            else:
                widget = parent

        screenRect = QW.QApplication.primaryScreen().availableGeometry()
        if widget != self: # there is a parent
            screenRect = widget.geometry()

        if self.alignment == QC.Qt.AlignCenter:
            centerRect = QW.QStyle.alignedRect(QC.Qt.LeftToRight, QC.Qt.AlignCenter, self.size(), screenRect)
            centerRect.setY(max(0, centerRect.y() - self.resultHeight * 4))
            self.setGeometry(centerRect)
        elif self.alignment == QC.Qt.AlignTop:
            rect = QW.QStyle.alignedRect(QC.Qt.LeftToRight, QC.Qt.AlignHCenter | QC.Qt.AlignTop, self.size(), screenRect)
            self.setGeometry(rect)

    def paintEvent(self, event):
        opt = QW.QStyleOption()
        opt.initFrom(self)
        p = QG.QPainter(self)
        self.style().drawPrimitive(QW.QStyle.PE_Widget, opt, p, self)

    def providerAdded(self, title: str, titleIconPath: str, suggestedReservedItemCount: int, hideTitle: bool):
        newTitleWidget = QLocatorTitleWidget(title, titleIconPath, self.titleHeight, hideTitle)
        self.visibleResultItemCounts.append(0)
        self.reservedItemCounts.append(suggestedReservedItemCount)
        self.titleItems.append(newTitleWidget)
        self.resultLayout.addWidget(newTitleWidget)
        newTitleWidget.setVisible(False)

        self.resultItems.append([])
        for i in range(suggestedReservedItemCount):
            newWidget = QLocatorResultWidget(self.searchEdit, self.resultHeight, self.primaryTextWidth, self.secondaryTextWidth, self)
            self.setupResultWidget(newWidget)
            self.resultItems[-1].append(newWidget)
            self.resultLayout.addWidget(newWidget)
            newWidget.setVisible(False)

    def setEscapeShortcuts(self, shortcuts):
        for escapeShortcut in self.escapeShortcuts:
            escapeShortcut.deleteLater()
        self.escapeShortcuts = []
        for shortcut in shortcuts:
            newShortcut = QW.QShortcut(QG.QKeySequence(shortcut), self)
            self.escapeShortcuts.append(newShortcut)
            newShortcut.activated.connect(self.finish)

    def setLocator(self, locator):
        if self.locator:
            self.locator.providerAdded.disconnect(self.providerAdded)
            self.locator.resultsAvailable.disconnect(self.handleResultsAvailable)

        self.reset()
        self.locator = locator

        if self.locator:
            for provider in self.locator.providers:
                self.providerAdded(provider.title(), self.locator.iconBasePath + provider.titleIconPath(), provider.suggestedReservedItemCount(), provider.hideTitle())
            self.locator.providerAdded.connect(self.providerAdded)
            self.locator.resultsAvailable.connect(self.handleResultsAvailable)

    def setDefaultStylingEnabled(self, enabled: bool) -> None:
        self.defaultStylingEnabled = enabled
        for i in range(len(self.resultItems)):
            for it in self.resultItems[i]: it.setDefaultStylingEnabled(enabled)

    def __del__(self):
        self.queryTimer.stop()
        if self.locator:
            if self.currentJobIds: self.locator.stopJobs(self.currentJobIds)
            self.locator.providerAdded.disconnect(self.providerAdded)
            self.locator.resultsAvailable.disconnect(self.handleResultsAvailable)
        for it in self.titleItems:
            it.deleteLater()
        for i in range(len(self.resultItems)):
            for it in self.resultItems[i]: it.deleteLater()

    def setContext(self, context):
        self.context = context

    def setQueryTimeout(self, msec: int):
        self.queryTimer.setInterval(msec)

    def start(self):
        self.clear()
        self.updateAlignment()
        self.show()
        self.searchEdit.setFocus()
        self.searchEdit.textEdited.emit("") # pylint: disable=E1101

    def finish(self, doNotStopJobs: bool = False):
        self.queryTimer.stop()
        if self.locator and self.currentJobIds and not doNotStopJobs: self.locator.stopJobs(self.currentJobIds)
        self.clear()
        self.hide()
        self.finished.emit()

    def reset(self):
        if self.locator and self.currentJobIds: self.locator.stopJobs(self.currentJobIds)
        self.currentJobIds.clear()
        self.reservedItemCounts.clear()
        self.visibleResultItemCounts.clear()
        for it in self.titleItems:
            it.deleteLater()
        self.titleItems = []
        for i in range(len(self.resultItems)):
            for it in self.resultItems[i]: it.deleteLater()
        self.resultItems = []
        if self.locator:
            for provider in self.locator.providers:
                self.providerAdded(provider.title(), self.locator.iconBasePath + provider.titleIconPath(), provider.suggestedReservedItemCount(), provider.hideTitle())

    def handleResultsAvailable(self, providerIndex: int, jobID: int) -> None:
        data = self.locator.getResult(jobID)
        self.titleItems[providerIndex].updateData(len(data))
        if not self.titleItems[providerIndex].shouldRemainHidden:
            self.setResultVisible(self.titleItems[providerIndex], len(data) != 0)
        if len(data): self.resultList.setVisible(True)

        if len(data) > len(self.resultItems[providerIndex]):
            titleItemIdx = 0
            for i in range(self.resultLayout.count()):
                if self.resultLayout.itemAt(i).widget() == self.titleItems[providerIndex]: break
                titleItemIdx += 1
            i = len(self.resultItems[providerIndex])
            while i < len(data):
                newWidget = QLocatorResultWidget(self.searchEdit, self.resultHeight, self.primaryTextWidth, self.secondaryTextWidth, self)
                self.setupResultWidget(newWidget)
                self.resultLayout.insertWidget(titleItemIdx + i + 1, newWidget)
                self.resultItems[providerIndex].append(newWidget)
                i += 1

        for i in range(len(self.resultItems[providerIndex])):
            if i < len(data):
                self.resultItems[providerIndex][i].updateData(providerIndex, data[i])
                if not self.resultItems[providerIndex][i].isVisible():
                    self.setResultVisible(self.resultItems[providerIndex][i], True)
            else:
                if self.resultItems[providerIndex][i].isVisible():
                    self.setResultVisible(self.resultItems[providerIndex][i], False)

        self.updateResultListHeight()

    def queryLocator(self, query: str) -> None:
        if not self.locator: return
        if self.currentJobIds:
            self.locator.stopJobs(self.currentJobIds)
        self.lastQuery = query
        self.queryTimer.start()

    def handleResultUp(self):
        resultWidget = self.sender()
        resultWidget.setSelected(False)
        i = self.selectedLayoutItemIndex - 1
        while i > 0:
            widget = self.resultLayout.itemAt(i).widget()
            if widget and widget.isVisible():
                if isinstance(widget, QLocatorResultWidget):
                    self.selectedLayoutItemIndex = i
                    widget.setSelected(True)
                    self.resultList.ensureVisible(0, widget.pos().y(), 0, 0)
                    return
            i = i - 1
        self.searchEdit.setFocus()
        self.resultList.ensureVisible(0, 0, 0, 0)

    def handleResultDown(self):
        resultWidget = self.sender()
        i = self.selectedLayoutItemIndex + 1
        while i < self.resultLayout.count():
            widget = self.resultLayout.itemAt(i).widget()
            if widget and widget.isVisible():
                if isinstance(widget, QLocatorResultWidget):
                    self.selectedLayoutItemIndex = i
                    resultWidget.setSelected(False)
                    widget.setSelected(True)
                    self.resultList.ensureVisible(0, widget.pos().y() + widget.height(), 0, 0)
                    break
            i = i + 1

    def handleEditorDown(self):
        for i in range(self.resultLayout.count()):
            widget = self.resultLayout.itemAt(i).widget()
            if widget and widget.isVisible():
                if isinstance(widget, QLocatorResultWidget):
                    self.selectedLayoutItemIndex = i
                    widget.setSelected(True)
                    break

    def handleEntered(self):
        resultWidget = self.sender()
        i = 0
        while i < self.resultLayout.count():
            widget = self.resultLayout.itemAt(i).widget()
            if widget and widget.isVisible() and isinstance(widget, QLocatorResultWidget):
                if widget == resultWidget:
                    self.selectedLayoutItemIndex = i
                    widget.setSelected(True)
                else:
                    widget.setSelected(False)
            i = i + 1

    def handleResultActivated(self, provider: int, id: int, closeOnSelected: bool):
        currJobIdsTmp = self.currentJobIds[:]
        if closeOnSelected: self.finish(True)
        if self.locator:
            self.locator.activateResult(provider, id)
            if closeOnSelected and currJobIdsTmp: self.locator.stopJobs(currJobIdsTmp)

    def clear(self):
        self.searchEdit.clear()
        self.queryTimer.stop()
        self.lastQuery = str()
        self.context = None
        for i in range(len(self.titleItems)):
            self.titleItems[i].setVisible(False)
            for it in self.resultItems[i]:
                it.setVisible(False)
                it.setSelected(False)
            self.visibleResultItemCounts[i] = 0
        self.deleteAdditionalItems()
        self.updateResultListHeight()

    def deleteAdditionalItems(self):
        titleIndex = 0
        for i in range(len(self.titleItems)):
            resultItemCount = len(self.resultItems[i])
            j = titleIndex
            while j < self.resultLayout.count():
                if self.resultLayout.itemAt(j).widget() == self.titleItems[i]: break
                titleIndex += 1
                j += 1
            k = self.reservedItemCounts[i]
            while k < resultItemCount:
                self.resultLayout.takeAt(titleIndex + self.reservedItemCounts[i] + 1).widget().deleteLater()
                k += 1
            self.resultItems[i] = self.resultItems[i][:self.reservedItemCounts[i]]

    def getVisibleHeight(self) -> int:
        itemCount = 0
        height = 0
        for i in range(len(self.titleItems)):
            if itemCount >= self.maxVisibleItemCount: break
            if self.visibleResultItemCounts[i] > 0:
                if not self.titleItems[i].shouldRemainHidden:
                    itemCount += 1
                    height += self.titleHeight
                if itemCount >= self.maxVisibleItemCount: break
                visibleItems = min(self.visibleResultItemCounts[i], self.maxVisibleItemCount - itemCount)
                itemCount += visibleItems
                height += self.resultHeight * visibleItems
        return height

    def setResultVisible(self, widget: QW.QWidget, visible: bool):
        if widget.isVisible() and not visible:
            widget.setVisible(False)
            if isinstance(widget, QLocatorResultWidget):
                self.visibleResultItemCounts[widget.providerIndex] -= 1
                widget.setSelected(False)
        elif not widget.isVisible() and visible:
            if isinstance(widget, QLocatorResultWidget):
                self.visibleResultItemCounts[widget.providerIndex] += 1
            widget.setVisible(True)

    def updateResultListHeight(self):
        pos = self.pos()
        visibleHeight = self.getVisibleHeight()
        if visibleHeight == 0:
            self.resultList.setVisible(False)
        else:
            self.resultList.setVisible(True)
            self.resultList.widget().setMaximumHeight(visibleHeight)
        if self.resultList.isVisible():
            self.setFixedHeight(self.searchEdit.sizeHint().height() + (self.resultList.height() - self.resultList.contentsRect().height()) + visibleHeight)
        else:
            self.setFixedHeight(self.searchEdit.sizeHint().height())
        self.move(pos)

    def setupResultWidget(self, widget):
        widget.up.connect(self.handleResultUp)
        widget.down.connect(self.handleResultDown)
        widget.activated.connect(self.handleResultActivated)
        widget.entered.connect(self.handleEntered)
        widget.setDefaultStylingEnabled(self.defaultStylingEnabled)

class QLocator(QC.QObject):
    iconBasePathChanged = QC.Signal(str)
    providerAdded = QC.Signal(str, str, int, bool)
    resultsAvailable = QC.Signal(int, int)
    def __init__(self, parent):
        super().__init__(parent)
        self.providers = []
        self.currentJobs = {}
        self.savedProviderData = {}
        self.jobIDCounter = 0
        self.iconBasePath = str()

    def addProvider(self, provider) -> None:
        self.providers.append(provider)
        provider.setParent(self)
        provider.resultsAvailable.connect(self.handleItemUpdate)
        self.providerAdded.emit(provider.title(), self.iconBasePath + provider.titleIconPath(), provider.suggestedReservedItemCount(), provider.hideTitle())

    def provider(self, idx: int):
        if idx >= 0 and idx <= len(self.providers):
            return self.providers[idx]
        return None

    def getResult(self, jobID: int):
        return self.savedProviderData.pop(jobID, None)

    def __del__(self):
        self.stopJobs()

    def setIconBasePath(self, iconBasePath: str) -> None:
        if self.iconBasePath != iconBasePath:
            self.iconBasePath = iconBasePath
            self.iconBasePathChanged.emit(self.iconBasePath)

    def query(self, queryText: str, context) -> list:
        jobIDs = []
        for i in range(len(self.providers)):
            self.currentJobs[self.jobIDCounter] = i
            jobIDs.append(self.jobIDCounter)
            self.providers[i].processQuery(queryText, context, self.jobIDCounter)
            self.jobIDCounter += 1
        return jobIDs

    def activateResult(self, provider: int, id: int) -> None:
        if provider >= 0 and provider < len(self.providers):
            self.providers[provider].resultSelected(id)

    def handleItemUpdate(self, jobID: int, data) -> None:
        if jobID in self.currentJobs:
            providerIndex = self.currentJobs[jobID]
            del self.currentJobs[jobID]
            self.savedProviderData[jobID] = data
            for dataItem in self.savedProviderData[jobID]:
                dataItem.defaultIconPath = self.iconBasePath + dataItem.defaultIconPath
                dataItem.selectedIconPath = self.iconBasePath + dataItem.selectedIconPath
                dataItem.toggledIconPath = self.iconBasePath + dataItem.toggledIconPath
                dataItem.toggledSelectedIconPath = self.iconBasePath + dataItem.toggledSelectedIconPath
            self.resultsAvailable.emit(providerIndex, jobID)

    def stopJobs(self, ids = []) -> None:
        if not len(ids):
            self.currentJobs = {}
            for provider in self.providers:
                provider.stopJobs([])
            self.savedProviderData = {}
        else:
            for provider in self.providers:
                provider.stopJobs(ids)
            for id in ids:
                if id in self.currentJobs:
                    del self.currentJobs[id]
                if id in self.savedProviderData:
                    del self.savedProviderData[id]
