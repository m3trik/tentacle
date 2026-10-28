# !/usr/bin/python
# coding=utf-8
"""The Create Attribute popup: a one-shot form over the host's attribute types."""


class AttributeForm:
    """Builds the Create Attribute popup.

    The host engine says which types it makes (``Channels.CREATE_TYPES``); the
    form shows the fields each type takes -- a numeric range, enum labels --
    and hands the values to the panel, which owns the selection and the
    engine call.
    """

    #: Types whose value carries no numeric range.
    UNRANGED = ("bool", "string", "enum")

    @classmethod
    def show(cls, sb, parent, types, on_create, keyable=True):
        """Build and show the form.

        Parameters:
            sb: The switchboard (its ``registered_widgets.Menu`` and
                ``FieldVisibility``).
            parent (QWidget): The panel's window.
            types (sequence[str]): The attribute types offered, in combo order.
            on_create (callable): Called with the form's values as keywords
                (``name``, ``attr_type``, ``keyable``, ``min_val``, ``max_val``,
                ``default_val``, ``enum_names``); returns True to close the form.
            keyable (bool): Whether the host has a per-attribute keyable flag.
                Without one the Keyable box shows checked and disabled: every
                attribute there is keyable.

        Returns:
            The shown menu.
        """
        menu = sb.registered_widgets.Menu(
            parent=parent,
            position="cursor",
            add_defaults_button=False,
            fixed_item_height=20,
        )
        menu.setTitle("Create Attribute")
        # Chrome is deferred to first show; build it now so the header exists
        # for the pin->hide swap below (this popup shows immediately).
        menu.ensure_chrome()
        # A one-shot form, not a pinnable tool panel: hide, not pin.
        if menu.header:
            menu.header.config_buttons("hide")

        menu.add("QLabel", setText="Name:", row=0, col=0)
        le_name = menu.add(
            "QLineEdit",
            setPlaceholderText="my_attribute",
            setObjectName="le_attr_name",
            row=0,
            col=1,
        )
        menu.add("QLabel", setText="Type:", row=1, col=0)
        cmb_type = menu.add(
            "QComboBox",
            setObjectName="cmb_attr_type",
            addItems=list(types),
            row=1,
            col=1,
        )

        range_fields = [menu.add("Separator", setTitle="Range", row=2)]
        spins = {}
        for row, (key, label, value) in enumerate(
            (("default", "Default:", 0.0), ("min", "Min:", 0.0), ("max", "Max:", 1.0)),
            start=3,
        ):
            range_fields.append(menu.add("QLabel", setText=label, row=row, col=0))
            spins[key] = menu.add(
                "QDoubleSpinBox",
                setObjectName=f"spn_{key}",
                setMinimum=-1e9,
                setMaximum=1e9,
                setValue=value,
                row=row,
                col=1,
            )
            range_fields.append(spins[key])

        enum_fields, le_enum = [], None
        if "enum" in types:
            enum_fields.append(menu.add("Separator", setTitle="Enum", row=6))
            enum_fields.append(menu.add("QLabel", setText="Names:", row=7, col=0))
            le_enum = menu.add(
                "QLineEdit",
                setPlaceholderText="A:B:C",
                setToolTip="Colon-separated enum labels.",
                setObjectName="le_enum_names",
                row=7,
                col=1,
            )
            enum_fields.append(le_enum)

        menu.add("Separator", row=8)
        chk_keyable = menu.add(
            "QCheckBox",
            setText="Keyable",
            setChecked=True,
            setObjectName="chk_keyable",
            row=9,
        )
        if not keyable:
            chk_keyable.setEnabled(False)
            chk_keyable.setToolTip("Every custom attribute is keyable here.")
        btn = menu.add(
            "QPushButton",
            setText="Create",
            setMinimumHeight=28,
            setMaximumHeight=28,
            row=10,
        )

        # Which fields each type shows: a table rather than a predicate, so a
        # type that names no fields shows none, and the popup re-fits to the
        # form it is now rather than keeping the height of the widest type.
        fields = sb.FieldVisibility()
        for attr_type in types:
            if attr_type not in cls.UNRANGED:
                fields.define(attr_type, range_fields)
        if enum_fields:
            fields.define("enum", enum_fields)
        fields.bind(cmb_type)

        def create():
            attr_type = cmb_type.currentText()
            closed = on_create(
                name=le_name.text().strip().replace(" ", "_"),
                attr_type=attr_type,
                keyable=chk_keyable.isChecked(),
                min_val=spins["min"].value(),
                max_val=spins["max"].value(),
                default_val=spins["default"].value(),
                enum_names=(
                    le_enum.text().strip()
                    if le_enum is not None and attr_type == "enum"
                    else ""
                ),
            )
            if closed:
                menu.hide()

        btn.clicked.connect(create)
        menu.show()
        return menu
