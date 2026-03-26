from PySide6.QtWidgets import QComboBox, QSpinBox, QLineEdit, QLabel, QDialogButtonBox

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)

class CustomSpinBox(QSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)        

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

class CustomLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)

class CustomDialogButtonBox(QDialogButtonBox):
    def __init__(self, parent=None):
        super().__init__(parent)

class CustomPushButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
