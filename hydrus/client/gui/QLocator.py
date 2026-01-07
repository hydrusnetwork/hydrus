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

import collections.abc

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from qtpy import QtGui as QG
import random
import math
import re

def elideRichText(richText: str, maxWidth: int, widget, elideFromLeft: bool):
    
    doc = QG.QTextDocument()
    opt = QG.QTextOption()
    opt.setWrapMode(QG.QTextOption.WrapMode.NoWrap)
    doc.setDefaultTextOption(opt)
    doc.setDocumentMargin(0)
    doc.setHtml(richText)
    doc.adjustSize()
    
    if doc.size().width() > maxWidth:
        cursor = QG.QTextCursor (doc)
        if elideFromLeft:
            cursor.movePosition(QG.QTextCursor.MoveOperation.Start)
        else:
            cursor.movePosition(QG.QTextCursor.MoveOperation.End)
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
            
            if event.type() == QC.QEvent.Type.FocusIn:
                
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
        hbox = QW.QHBoxLayout()
        self.setLayout(hbox)
        self.iconLabel = QW.QLabel()
        self.iconLabel.setFixedHeight(self.iconHeight)
        self.iconLabel.setPixmap(self.icon.pixmap(self.iconHeight, self.iconHeight))
        self.titleLabel = QW.QLabel()
        self.titleLabel.setText(title)
        self.titleLabel.setTextFormat(QC.Qt.TextFormat.RichText)
        self.countLabel = QW.QLabel()
        hbox.setContentsMargins(4, 1, 4, 1)
        hbox.addWidget(self.iconLabel)
        hbox.addWidget(self.titleLabel)
        hbox.addStretch(1)
        hbox.addWidget(self.countLabel)
        hbox.setAlignment(self.countLabel, QC.Qt.AlignmentFlag.AlignVCenter)
        hbox.setAlignment(self.iconLabel, QC.Qt.AlignmentFlag.AlignVCenter)
        hbox.setAlignment(self.titleLabel, QC.Qt.AlignmentFlag.AlignVCenter)
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
    pageUp = QC.Signal()
    pageDown = QC.Signal()
    home = QC.Signal()
    end = QC.Signal()
    activated = QC.Signal(int, int, bool)
    entered = QC.Signal()
    def __init__(self, keyEventTarget: QW.QWidget, height: int, primaryTextWidth: int, secondaryTextWidth: int, parent = None):
        super().__init__(parent)
        self.iconHeight = height - 2
        self.setObjectName("unselectedLocatorResult")
        self.keyEventTarget = keyEventTarget
        hbox = QW.QHBoxLayout()
        self.setLayout( hbox )
        self.iconLabel = QW.QLabel(self)
        self.iconLabel.setFixedHeight(self.iconHeight)
        self.mainTextLabel = QW.QLabel(self)
        self.primaryTextWidth = primaryTextWidth
        self.mainTextLabel.setMinimumWidth(primaryTextWidth)
        self.mainTextLabel.setTextFormat(QC.Qt.TextFormat.RichText)
        self.mainTextLabel.setTextInteractionFlags(QC.Qt.TextInteractionFlag.NoTextInteraction)
        self.secondaryTextLabel = QW.QLabel(self)
        self.secondaryTextWidth = secondaryTextWidth
        self.secondaryTextLabel.setMaximumWidth(secondaryTextWidth)
        self.secondaryTextLabel.setTextFormat(QC.Qt.TextFormat.RichText)
        self.secondaryTextLabel.setTextInteractionFlags(QC.Qt.TextInteractionFlag.NoTextInteraction)
        hbox.setContentsMargins(4, 1, 4, 1)
        hbox.addWidget(self.iconLabel)
        hbox.addWidget(self.mainTextLabel)
        hbox.addStretch(1)
        hbox.addWidget(self.secondaryTextLabel)
        hbox.setAlignment(self.mainTextLabel, QC.Qt.AlignmentFlag.AlignVCenter)
        hbox.setAlignment(self.iconLabel, QC.Qt.AlignmentFlag.AlignVCenter)
        hbox.setAlignment(self.secondaryTextLabel, QC.Qt.AlignmentFlag.AlignVCenter)
        self.setFixedHeight(height)
        self.setSizePolicy(QW.QSizePolicy.Policy.Expanding, QW.QSizePolicy.Policy.Fixed)
        self.activateEnterShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key.Key_Enter), self)
        self.activateEnterShortcut.setContext(QC.Qt.ShortcutContext.WidgetShortcut)
        self.activateReturnShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key.Key_Return), self)
        self.activateReturnShortcut.setContext(QC.Qt.ShortcutContext.WidgetShortcut)
        self.upShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key.Key_Up), self)
        self.upShortcut.setContext(QC.Qt.ShortcutContext.WidgetShortcut)
        self.downShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key.Key_Down), self)
        self.downShortcut.setContext(QC.Qt.ShortcutContext.WidgetShortcut)
        self.pageUpShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_PageUp ), self )
        self.pageUpShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.pageDownShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_PageDown ), self )
        self.pageDownShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.homeShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_Home ), self )
        self.homeShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.endShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_End ), self )
        self.endShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        
        self.selectedPalette = self.palette()
        self.selectedPalette.setColor(QG.QPalette.ColorRole.Window, QG.QPalette().color(QG.QPalette.ColorRole.WindowText))
        self.selectedPalette.setColor(QG.QPalette.ColorRole.WindowText, QG.QPalette().color(QG.QPalette.ColorRole.Window))

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

        self.upShortcut.activated.connect( self.up )
        self.downShortcut.activated.connect( self.down )
        self.pageUpShortcut.activated.connect( self.pageUp )
        self.pageDownShortcut.activated.connect( self.pageDown )
        self.homeShortcut.activated.connect( self.home )
        self.endShortcut.activated.connect( self.end )

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
            self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Mode.Selected if self.selected else QG.QIcon.Mode.Normal))
        self.activated.emit(self.providerIndex, self.id, self.closeOnActivated)

    def updateData(self, providerIndex: int, data: QLocatorSearchResult):
        self.toggled = data.toggled
        self.currentIcon = QG.QIcon()
        self.currentIcon.addFile(data.defaultIconPath, QC.QSize(), QG.QIcon.Mode.Normal)
        self.currentIcon.addFile(data.selectedIconPath, QC.QSize(), QG.QIcon.Mode.Selected)
        self.currentToggledIcon = QG.QIcon()
        self.currentToggledIcon.addFile(data.toggledIconPath, QC.QSize(), QG.QIcon.Mode.Normal)
        self.currentToggledIcon.addFile(data.toggledSelectedIconPath, QC.QSize(), QG.QIcon.Mode.Selected)
        iconToUse = self.currentIcon if not self.toggled else self.currentToggledIcon
        self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Mode.Selected if self.selected else QG.QIcon.Mode.Normal))
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
        self.iconLabel.setPixmap(iconToUse.pixmap(self.iconHeight, self.iconHeight, QG.QIcon.Mode.Selected if self.selected else QG.QIcon.Mode.Normal))

    def keyPressEvent(self, ev: QG.QKeyEvent):
        if ev.key() != QC.Qt.Key.Key_Up and ev.key() != QC.Qt.Key.Key_Down and ev.key() != QC.Qt.Key.Key_Enter and ev.key() != QC.Qt.Key.Key_Return:
            QW.QApplication.postEvent(self.keyEventTarget, QG.QKeyEvent(ev.type(), ev.key(), ev.modifiers(), ev.text(), ev.isAutoRepeat()))
            self.keyEventTarget.setFocus()
        else:
            super().keyPressEvent( ev )

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

# hydev tore the selection and navigation stuff apart and rewrote it
# also added char threshold
class QLocatorWidget(QW.QWidget):
    finished = QC.Signal()
    def __init__(
        self,
        parent = None,
        width: int = 600,
        resultHeight: int = 36,
        titleHeight: int = 36,
        primaryTextWidth: int = 320,
        secondaryTextWidth: int = 200,
        maxVisibleItemCount: int = 8
    ):
        
        super().__init__( parent )
        
        self.alignment = QC.Qt.AlignmentFlag.AlignCenter
        self.resultHeight = resultHeight
        self.titleHeight = titleHeight
        self.primaryTextWidth = primaryTextWidth
        self.locator = None
        self.secondaryTextWidth = secondaryTextWidth
        self.maxVisibleItemCount = maxVisibleItemCount
        self.reservedItemCounts = []
        self.visibleResultItemCounts = []
        self.currentJobIds = []
        self.providerDisplayOrder = []
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
        self.resultLayout.setSizeConstraint(QW.QLayout.SizeConstraint.SetMinAndMaxSize)
        self.layout().addWidget(self.searchEdit)
        self.layout().addWidget(self.resultList)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        self.resultLayout.setContentsMargins(0, 0, 0, 0)
        self.resultLayout.setSpacing(0)
        self.setFixedWidth(width)
        self.setWindowFlags(QC.Qt.WindowType.FramelessWindowHint | QC.Qt.WindowType.WindowStaysOnTopHint | QC.Qt.WindowType.CustomizeWindowHint | QC.Qt.WindowType.Popup)
        self.resultList.setSizeAdjustPolicy(QW.QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.setSizePolicy(QW.QSizePolicy.Policy.Fixed, QW.QSizePolicy.Policy.Maximum)
        self.setEscapeShortcuts([QC.Qt.Key.Key_Escape])
        self.editorUpShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_Up ), self.searchEdit )
        self.editorUpShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.editorUpShortcut.activated.connect( self.handleEditorUp )
        self.editorDownShortcut = QW.QShortcut(QG.QKeySequence(QC.Qt.Key.Key_Down), self.searchEdit)
        self.editorDownShortcut.setContext(QC.Qt.ShortcutContext.WidgetShortcut)
        self.editorDownShortcut.activated.connect(self.handleEditorDown)
        self.editorPageUpShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_PageUp ), self.searchEdit )
        self.editorPageUpShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.editorPageUpShortcut.activated.connect( self.handleEditorPageUp )
        self.editorPageDownShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_PageDown ), self.searchEdit )
        self.editorPageDownShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.editorPageDownShortcut.activated.connect( self.handleEditorPageDown )
        self.editorEndShortcut = QW.QShortcut( QG.QKeySequence( QC.Qt.Key.Key_End ), self.searchEdit )
        self.editorEndShortcut.setContext( QC.Qt.ShortcutContext.WidgetShortcut )
        self.editorEndShortcut.activated.connect( self.handleResultPageEnd )
        
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
        
    
    def _selectBottommostItem( self ):
        
        for i in range( self.resultLayout.count() - 1, -1, -1 ):
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    break
                    
                
            
        
    
    def _selectItem( self, index: int ):
        
        if self.selectedLayoutItemIndex != index:
            
            old_selected_layout_item = self.resultLayout.itemAt( self.selectedLayoutItemIndex )
            
            if old_selected_layout_item is not None:
                
                old_selected_widget = old_selected_layout_item.widget()
                
                if isinstance( old_selected_widget, QLocatorResultWidget ):
                    
                    old_selected_widget.setSelected( False )
                    
                
            
        
        widget = self.resultLayout.itemAt( index ).widget()
        
        if isinstance( widget, QLocatorResultWidget ):
            
            self.selectedLayoutItemIndex = index
            
            widget.setSelected( True )
            
            self.resultList.ensureVisible( 0, widget.pos().y(), 0, 0 )
            self.resultList.ensureVisible( 0, widget.pos().y() + widget.height(), 0, 0 )
            
        
    
    def _selectTopmostItem( self ):
        
        # ensure we are scrolled to the very top so a non-selectable title is visible
        
        self.resultList.ensureVisible( 0, 0, 0, 0 )
        
        # select the topmost selectable item
        
        for i in range( self.resultLayout.count() ):
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    break
                    
                
            
        
    
    def setAlignment( self, alignment ):
        if alignment == QC.Qt.AlignmentFlag.AlignCenter:
            self.alignment = alignment
            self.updateAlignment()
        elif alignment == QC.Qt.AlignmentFlag.AlignTop:
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

        if self.alignment == QC.Qt.AlignmentFlag.AlignCenter:
            centerRect = QW.QStyle.alignedRect(QC.Qt.LayoutDirection.LeftToRight, QC.Qt.AlignmentFlag.AlignCenter, self.size(), screenRect)
            centerRect.setY(max(0, centerRect.y() - self.resultHeight * 4))
            self.setGeometry(centerRect)
        elif self.alignment == QC.Qt.AlignmentFlag.AlignTop:
            rect = QW.QStyle.alignedRect(QC.Qt.LayoutDirection.LeftToRight, QC.Qt.AlignmentFlag.AlignHCenter | QC.Qt.AlignmentFlag.AlignTop, self.size(), screenRect)
            self.setGeometry(rect)

    def paintEvent(self, event):
        opt = QW.QStyleOption()
        opt.initFrom(self)
        p = QG.QPainter(self)
        self.style().drawPrimitive(QW.QStyle.PE_Widget, opt, p, self)

    def providerAdded( self, title: str, titleIconPath: str, suggestedReservedItemCount: int, hideTitle: bool ):
        
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
                self.providerAdded(provider.title(), self.locator.getIconPath( provider.titleIconPath() ), provider.suggestedReservedItemCount(), provider.hideTitle())
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
                self.providerAdded(provider.title(), self.locator.getIconPath( provider.titleIconPath() ), provider.suggestedReservedItemCount(), provider.hideTitle())

    def handleResultsAvailable(self, providerIndex: int, jobID: int) -> None:
        
        data = self.locator.getResult(jobID)
        data_length = len( data )
        
        self.titleItems[ providerIndex ].updateData( data_length )
        
        if not self.titleItems[ providerIndex ].shouldRemainHidden and providerIndex in self.providerDisplayOrder:
            
            self.setResultVisible( self.titleItems[ providerIndex ], data_length != 0 )
            
        
        if data_length:
            
            self.resultList.setVisible(True)
            
        
        if data_length > len( self.resultItems[ providerIndex ] ):
            
            titleItemIdx = 0
            
            for i in range( self.resultLayout.count() ):
                
                if self.resultLayout.itemAt(i).widget() == self.titleItems[providerIndex]: 
                    break
                
                titleItemIdx += 1
                
            
            i = len(self.resultItems[providerIndex])
            
            while i < data_length:
                
                newWidget = QLocatorResultWidget(self.searchEdit, self.resultHeight, self.primaryTextWidth, self.secondaryTextWidth, self)
                
                self.setupResultWidget(newWidget)
                
                self.resultLayout.insertWidget( titleItemIdx + i + 1, newWidget )
                self.resultItems[ providerIndex ].append( newWidget )
                
                i += 1
                
            
        
        for i in range( len( self.resultItems[ providerIndex ] ) ):
            
            if i < data_length:
                
                self.resultItems[ providerIndex ][ i ].updateData( providerIndex, data[ i ] )
                
                if not self.resultItems[ providerIndex ][ i ].isVisible() and providerIndex in self.providerDisplayOrder:
                    
                    self.setResultVisible( self.resultItems[ providerIndex ][ i ], True )
                    
                
            else:
                
                if self.resultItems[ providerIndex ][ i ].isVisible():
                    
                    self.setResultVisible( self.resultItems[ providerIndex ][ i ], False )
                    
                
        try:
            #this is where we reorganize the widgets based on the desired display order. items removed by the user are already hidden based on "providerIndex in self.providerDisplayOrder" above
            desired_widget_order = []
            
            for provider_idx in self.providerDisplayOrder:
                
                desired_widget_order.append( self.titleItems[ provider_idx ] )
                desired_widget_order.extend( self.resultItems[ provider_idx ] )
                
            
            for widget in desired_widget_order:
                
                self.resultLayout.removeWidget( widget )
                
            
            for idx, widget in enumerate( desired_widget_order ):
                
                self.resultLayout.insertWidget( idx, widget )
                
            
        except Exception:
            
            pass
            
        
        self.updateResultListHeight()
        
    
    def queryLocator(self, query: str) -> None:
        if not self.locator: return
        if self.currentJobIds:
            self.locator.stopJobs(self.currentJobIds)
        
        self.lastQuery = query
        self.queryTimer.start()
    
    def handleResultUp( self ):
        
        i = self.selectedLayoutItemIndex - 1
        
        while i > 0:
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    return
                    
                
            
            i = i - 1
            
        
        # nothing selectable above the current item, so let's scroll to top to show any title and focus the input
        
        self.resultList.ensureVisible( 0, 0, 0, 0 )
        self.searchEdit.setFocus()
        
    
    def handleResultDown( self ):
        
        i = self.selectedLayoutItemIndex + 1
        
        while i < self.resultLayout.count():
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    return
                    
                
            
            i = i + 1
            
        
        # nothing selectable below the current item, so let's wraparound and select the top item
        
        self._selectTopmostItem()
        
    
    def handleResultPageUp( self ):
        
        pageSize = self.getVisibleItems()
        
        i = self.selectedLayoutItemIndex - 1
        
        num_items_jumped = 1
        
        while i >= 0:
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                num_items_jumped += 1
                
                if num_items_jumped >= pageSize and isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    return
                    
                
            
            i = i - 1
            
        
        # we rolled over the end of the list and should clip to the topmost guy
        
        self._selectTopmostItem()
        
    
    def handleResultPageDown( self ):
        
        pageSize = self.getVisibleItems()
        
        i = self.selectedLayoutItemIndex + 1
        
        num_items_jumped = 1
        
        last_item_index = self.resultLayout.count() - 1
        
        while i <= last_item_index:
            
            widget = self.resultLayout.itemAt( i ).widget()
            
            if widget and widget.isVisible():
                
                num_items_jumped += 1
                
                if num_items_jumped >= pageSize and isinstance( widget, QLocatorResultWidget ):
                    
                    self._selectItem( i )
                    
                    return
                    
                
            
            i = i + 1
            
        
        # we rolled over the end of the list and should clip to the bottommost guy
        
        self._selectBottommostItem()
        
    
    def handleResultPageEnd( self ):
        
        self._selectBottommostItem()
        
    
    def handleResultPageHome( self ):
        
        self._selectTopmostItem()
        
    
    def handleEditorDown( self ):
        
        self._selectTopmostItem()
        
    
    def handleEditorUp(self):
        
        self._selectBottommostItem()
        
    
    def handleEditorPageDown( self ):
        
        self._selectTopmostItem()
        self.handleResultPageDown()
        
    
    def handleEditorPageUp( self ):
        
        self._selectBottommostItem()
        self.handleResultPageUp()
        
    
    def handleEntered(self):
        resultWidget = self.sender()
        i = 0
        while i < self.resultLayout.count():
            widget = self.resultLayout.itemAt(i).widget()
            if widget and widget.isVisible() and isinstance(widget, QLocatorResultWidget):
                if widget == resultWidget:
                    self._selectItem( i )
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
                layout_item = self.resultLayout.takeAt(titleIndex + self.reservedItemCounts[i] + 1)
                
                if layout_item is not None:
                    
                    layout_item.widget().deleteLater()
                    
                
                k += 1
            self.resultItems[i] = self.resultItems[i][:self.reservedItemCounts[i]]

    def getVisibleHeight( self ) -> int:
        
        height, _ = self.getVisibleNums()
        return height
        
    
    def getVisibleItems( self ) -> int:
        
        _, itemCount = self.getVisibleNums()
        return itemCount
        
    
    def getVisibleNums( self ) -> tuple[ int, int ]:
        
        itemCount = 0
        height = 0
        
        for i in range( len( self.titleItems ) ):
            
            if itemCount >= self.maxVisibleItemCount: 
                
                break
                
            
            if self.visibleResultItemCounts[i] > 0:
                
                if not self.titleItems[i].shouldRemainHidden:
                    
                    itemCount += 1
                    height += self.titleHeight
                    
                
                if itemCount >= self.maxVisibleItemCount: 
                    
                    break
                    
                visibleItems = min( self.visibleResultItemCounts[i], self.maxVisibleItemCount - itemCount )
                itemCount += visibleItems
                height += self.resultHeight * visibleItems
                
            
        return height, itemCount
        
    
    def getFirstVisibleResult( self ) -> int | None:
        
        for index in range( self.resultLayout.count() ):
            
            widget = self.resultLayout.itemAt( index ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    return index
                    
                
            
        
        return None
        
    
    def getLastVisibleResult( self ) -> int | None:
        
        for index in range( self.resultLayout.count() - 1, -1, -1 ):
            
            widget = self.resultLayout.itemAt( index ).widget()
            
            if widget and widget.isVisible():
                
                if isinstance( widget, QLocatorResultWidget ):
                    
                    return index
                    
                
            
        
        return None
        
    
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
        
    
    def updateOptions( self ):
        
        import hydrus.client.ClientGlobals as CG
        
        self.providerDisplayOrder = CG.client_controller.new_options.GetIntegerList( 'command_palette_provider_order' )
        
    
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
        widget.pageUp.connect( self.handleResultPageUp )
        widget.pageDown.connect( self.handleResultPageDown )
        widget.home.connect( self.handleResultPageHome )
        widget.end.connect( self.handleResultPageEnd )
        widget.activated.connect(self.handleResultActivated)
        widget.entered.connect(self.handleEntered)
        widget.setDefaultStylingEnabled(self.defaultStylingEnabled)

class QLocator(QC.QObject):
    
    providerAdded = QC.Signal(str, str, int, bool)
    resultsAvailable = QC.Signal(int, int)
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.providers = []
        self.savedProviderData = {}
        
        self.currentJobs = {}
        self.jobIDCounter = 0
        
        self.iconPathFactory = None
        
    
    def addProvider( self, provider ) -> None:
        
        self.providers.append(provider)
        
        provider.setParent(self)
        
        provider.resultsAvailable.connect( self.handleItemUpdate )
        
        self.providerAdded.emit( provider.title(), self.getIconPath( provider.titleIconPath() ), provider.suggestedReservedItemCount(), provider.hideTitle() )
        
    
    def provider(self, idx: int):
        
        if idx >= 0 and idx <= len(self.providers):
            
            return self.providers[idx]
            
        return None
        
    
    def getIconPath( self, filename ):
        
        if self.iconPathFactory is None:
            
            raise Exception( 'No way to determine icons for the Locator!' )
            
        
        return self.iconPathFactory( filename ) 
        
    
    def getResult(self, jobID: int):
        return self.savedProviderData.pop(jobID, None)

    def __del__(self):
        self.stopJobs()

    def setIconPathFactory(self, iconPathFactory: collections.abc.Callable[ [ str ], str ] ) -> None:
        
        self.iconPathFactory = iconPathFactory
        
    
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
                dataItem.defaultIconPath = self.getIconPath( dataItem.defaultIconPath )
                dataItem.selectedIconPath = self.getIconPath( dataItem.selectedIconPath )
                dataItem.toggledIconPath = self.getIconPath( dataItem.toggledIconPath )
                dataItem.toggledSelectedIconPath = self.getIconPath( dataItem.toggledSelectedIconPath )
            self.resultsAvailable.emit(providerIndex, jobID)

    def stopJobs(self, ids = None) -> None:
        
        if ids is None:
            
            ids = []
            
        
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
