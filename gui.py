    def add_destination_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة وجهة")
        layout = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("اسم الوجهة (مثال: قناة عاجل)")
        layout.addRow("الاسم:", name_edit)
        type_combo = QComboBox()
        type_combo.addItems(["channel", "group", "private"])
        layout.addRow("النوع:", type_combo)
        identifier_edit = QLineEdit()
        identifier_edit.setPlaceholderText("معرف الوجهة (يوزر القناة أو معرف الدردشة)")
        layout.addRow("المعرف:", identifier_edit)
        method_combo = QComboBox()
        method_combo.addItems(["forward", "copy", "text_only"])
        method_combo.setToolTip("forward: إعادة توجيه سريع (يحتفظ بالوسائط)\ncopy: نسخ مع تعديل النص\ntext_only: إرسال نص فقط")
        layout.addRow("طريقة الإرسال:", method_combo)
        cb_active = QCheckBox("نشط")
        cb_active.setChecked(True)
        layout.addRow(cb_active)
        btn_save = QPushButton("حفظ")
        layout.addRow(btn_save)
        dialog.setLayout(layout)

        def save():
            name = name_edit.text().strip()
            if not name:
                QMessageBox.warning(dialog, "خطأ", "الاسم مطلوب")
                return
            identifier = identifier_edit.text().strip()
            if not identifier:
                QMessageBox.warning(dialog, "خطأ", "المعرف مطلوب")
                return
            session = DbSession()
            dest = Destination(
                name=name,
                type=type_combo.currentText(),
                identifier=identifier,
                is_active=cb_active.isChecked(),
                send_method=method_combo.currentText()
            )
            dest.set_rules({})
            session.add(dest)
            session.commit()
            session.close()
            self.refresh_destinations()
            dialog.accept()
        btn_save.clicked.connect(save)
        dialog.exec_()
