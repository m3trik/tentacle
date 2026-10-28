# !/usr/bin/python
# coding=utf-8
"""A tween-tree row that sorts its numeric columns by number."""

from qtpy import QtCore, QtWidgets


class NumericSortItem(QtWidgets.QTreeWidgetItem):
    """A tree row that sorts the Weight and Frame columns by number.

    A plain ``QTreeWidgetItem`` sorts its text, so frame "10" would sort
    before "5". This reads the cell's :attr:`NUM_ROLE` number when present
    (the panel sets it) and falls back to the text.
    """

    NUM_ROLE = QtCore.Qt.UserRole + 1

    def __lt__(self, other: "QtWidgets.QTreeWidgetItem") -> bool:
        col = self.treeWidget().sortColumn() if self.treeWidget() else 0
        a = self.data(col, self.NUM_ROLE)
        b = other.data(col, self.NUM_ROLE)
        if a is not None and b is not None:
            return a < b
        return self.text(col) < other.text(col)
