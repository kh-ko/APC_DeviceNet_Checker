from __future__ import annotations
import sys
from PySide6.QtCore import QObject, Slot, Signal
import typing

print("Starting tests with __future__ annotations...")

# 7. Using | in @Slot with __future__
try:
    class TestObj7(QObject):
        @Slot(int, bytes | None)
        def test_slot(self, a, b):
            print(a, b)
    print("Test 7 (| in @Slot with __future__): Success")
except Exception as e:
    print(f"Test 7: Failed: {e}")

print("Tests completed.")
