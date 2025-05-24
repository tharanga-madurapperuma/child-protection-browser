# bridge.py
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

class JSBridge(QObject):
    domChanged = pyqtSignal()  # Signal to notify Python

    @pyqtSlot()
    def notifyDomChanged(self):
        print("[JSBridge] DOM changed detected!")
        self.domChanged.emit()
