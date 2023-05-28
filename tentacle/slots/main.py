# !/usr/bin/python
# coding=utf-8
from uitk.switchboard import signals
from tentacle.slots import Slots


class Main(Slots):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        """
        """

    def list000_init(self, root):
        """ """
        print("list000_init:", root)
        root.sublist_x_offset = -19

        w1 = root.add("QPushButton", setText="Recent Commands")
        w2 = root.add("QPushButton", setText="History")

    @signals("on_item_interacted")
    def list000(self, item):
        """ """
        print("list000:", item)

        # if (
        #     not w
        # ):  # code here will run before each show event. generally used to refresh list contents. ------------------
        #     # command history
        #     recentCommandInfo = [
        #         m.__name__ for m in self.sb.prev_commands
        #     ]  # Get a list of any recently called method names.
        #     # w1 = widget.getItemWidgetsByText('Recent Commands')[0]
        #     w1 = widget.getItemsByText("Recent Commands")[0]
        #     # print (0, w1)
        #     widget._addList(w1)
        #     # print (1, w1.sublist)
        #     w2 = w1.sublist.add("QPushButton", setObjectName="b004", setText="Button 4")
        #     # [w1.sublist.add('QLabel', setText=m.__doc__) for m in recentCommandInfo]
        #     return

        # # print (w.text(), w, w.sublist)
        # if w.text == "Recent Commands":
        #     recentCommands = (
        #         self.sb.prev_commands
        #     )  # Get a list of any previously called slot methods.
        #     method = recentCommands[index]
        #     if callable(method):
        #         method()
