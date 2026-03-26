import sys
from PySide6.QtCore import QObject, Slot, Signal
import typing

print("Starting tests with string-based types...")

# 5. Using "bytes | None" AS A STRING in @Slot
try:
    class TestObj5(QObject):
        @Slot(int, "bytes | None")
        def test_slot(self, a, b):
            print(a, b)
    print("Test 5 (string '|' in @Slot): Success")
except Exception as e:
    print(f"Test 5: Failed: {e}")

# 6. Using "QByteArray" in @Slot
try:
    class TestObj6(QObject):
        @Slot(int, "QByteArray")
        def test_slot(self, a, b):
            print(a, b)
    print("Test 6 (string 'QByteArray' in @Slot): Success")
except Exception as e:
    print(f"Test 6: Failed: {e}")

print("Tests completed.")
