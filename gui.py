import sys
import asyncio
import logging
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import qasync
from qasync import QApplication, asyncSlot, asyncClose
from typing import Dict, List
from models import Session as DbSession, Account, Channel, Post, Destination, Keyword
from telegram_client import TelegramManager
from ai_engine import ai_engine
from translation import translator
from rules_engine import rules_engine
import config
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.telegram_manager = TelegramManager()
        self.telegram_manager.set_message_handler(self.on_new_message)
        self.setWindowTitle("Telegram Monitor - AI Powered")
        self.setGeometry(100, 100, 1400, 800)
        self.init_ui()
        self.load_data()
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_stats)
        self.timer.start(5000)

    def init_ui(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "لوحة التحكم")
        self.setup_dashboard()

        self.accounts_tab = QWidget()
        self.tabs.addTab(self.accounts_tab, "الحسابات")
        self.setup_accounts_tab()

        self.channels_tab = QWidget()
        self.tabs.addTab(self.channels_tab, "قنوات الرصد")
        self.setup_channels_tab()

        self.live_tab = QWidget()
        self.tabs.addTab(self.live_tab, "الرصد المباشر (الكل)")
        self.setup_live_tab()

        self.media_tab = QWidget()
        self.tabs.addTab(self.media_tab, "الوسائط (صور/فيديو)")
        self.setup_media_tab()

        self.text_tab = QWidget()
        self.tabs.addTab(self.text_tab, "الأخبار النصية")
        self.setup_text_tab()

        self.destinations_tab = QWidget()
        self.tabs.addTab(self.destinations_tab, "وجهات الإرسال")
        self.setup_destinations_tab()

        self.settings_tab = QWidget()
        self.tabs.addTab(self.settings_tab, "الإعدادات")
        self.setup_settings_tab()

    def setup_dashboard(self):
        layout = QVBoxLayout()
        stats_layout = QHBoxLayout()
        self.lbl_accounts = QLabel("الحسابات: 0")
        self.lbl_channels = QLabel("القنوات المراقبة: 0")
        self.lbl_posts_today = QLabel("المنشورات اليوم: 0")
        self.lbl_urgent = QLabel("عاجل اليوم: 0")
        stats_layout.addWidget(self.lbl_accounts)
        stats_layout.addWidget(self.lbl_channels)
        stats_layout.addWidget(self.lbl_posts_today)
        stats_layout.addWidget(self.lbl_urgent)
        layout.addLayout(stats_layout)

        self.status_label = QLabel("الحالة: جاهز")
        layout.addWidget(self.status_label)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        layout.addWidget(QLabel("سجل الأحداث:"))
        layout.addWidget(self.event_log)
        self.dashboard_tab.setLayout(layout)

    def setup_accounts_tab(self):
        layout = QVBoxLayout()
        btn_add = QPushButton("إضافة حساب")
        btn_add.clicked.connect(self.add_account_dialog)
        layout.addWidget(btn_add)

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(4)
        self.accounts_table.setHorizontalHeaderLabels(["الهاتف", "رئيسي", "الحالة", "القنوات"])
        layout.addWidget(self.accounts_table)
        self.accounts_tab.setLayout(layout)

    def setup_channels_tab(self):
        layout = QVBoxLayout()
        btn_layout = QHBoxLayout()
        btn_sync = QPushButton("جلب القنوات من الحساب الرئيسي")
        btn_sync.clicked.connect(self.sync_channels)
        btn_select_all = QPushButton("تحديد الكل")
        btn_select_all.clicked.connect(self.select_all_channels)
        btn_deselect_all = QPushButton("إلغاء تحديد الكل")
        btn_deselect_all.clicked.connect(self.deselect_all_channels)
        btn_save = QPushButton("حفظ التحديدات")
        btn_save.clicked.connect(self.save_channel_selection)
        btn_layout.addWidget(btn_sync)
        btn_layout.addWidget(btn_select_all)
        btn_layout.addWidget(btn_deselect_all)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

        self.channels_tree = QTreeWidget()
        self.channels_tree.setHeaderLabels(["القناة", "يوزر", "مراقبة"])
        self.channels_tree.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.channels_tree)
        self.channels_tab.setLayout(layout)

    def setup_live_tab(self):
        layout = QVBoxLayout()
        self.live_list = QListWidget()
        self.live_list.itemDoubleClicked.connect(self.show_post_details)
        layout.addWidget(self.live_list)
        self.live_tab.setLayout(layout)

    def setup_media_tab(self):
        layout = QVBoxLayout()
        self.media_list = QListWidget()
        self.media_list.itemDoubleClicked.connect(self.show_post_details)
        layout.addWidget(self.media_list)
        self.media_tab.setLayout(layout)

    def setup_text_tab(self):
        layout = QVBoxLayout()
        self.text_list = QListWidget()
        self.text_list.itemDoubleClicked.connect(self.show_post_details)
        layout.addWidget(self.text_list)
        self.text_tab.setLayout(layout)

    def setup_destinations_tab(self):
        layout = QVBoxLayout()
        btn_add = QPushButton("إضافة وجهة")
        btn_add.clicked.connect(self.add_destination_dialog)
        layout.addWidget(btn_add)

        self.destinations_list = QListWidget()
        layout.addWidget(self.destinations_list)
        self.destinations_tab.setLayout(layout)

    def setup_settings_tab(self):
        layout = QVBoxLayout()
        group = QGroupBox("الذكاء الاصطناعي")
        group_layout = QFormLayout()
        self.ai_check = QCheckBox("تفعيل الذكاء الاصطناعي (تصنيف، أهمية، تكرار)")
        self.ai_check.setChecked(True)
        group_layout.addRow(self.ai_check)
        group.setLayout(group_layout)
        layout.addWidget(group)

        group2 = QGroupBox("الترجمة")
        group2_layout = QFormLayout()
        self.translate_check = QCheckBox("تفعيل الترجمة التلقائية")
        self.translate_check.setChecked(True)
        group2_layout.addRow(self.translate_check)
        group2.setLayout(group2_layout)
        layout.addWidget(group2)

        group3 = QGroupBox("الكلمات المفتاحية")
        group3_layout = QVBoxLayout()
        self.keywords_list = QListWidget()
        group3_layout.addWidget(self.keywords_list)
        btn_add_kw = QPushButton("إضافة كلمة مفتاحية")
        btn_add_kw.clicked.connect(self.add_keyword_dialog)
        group3_layout.addWidget(btn_add_kw)
        group3.setLayout(group3_layout)
        layout.addWidget(group3)

        btn_reset = QPushButton("إعادة ضبط الإعدادات الافتراضية")
        btn_reset.clicked.connect(self.reset_settings)
        layout.addWidget(btn_reset)
        self.settings_tab.setLayout(layout)

    # دوال تحميل البيانات
    def load_data(self):
        self.refresh_accounts()
        self.refresh_channels()
        self.refresh_stats()
        self.refresh_destinations()
        self.refresh_keywords()
        rules_engine.set_telegram_manager(self.telegram_manager)

    def refresh_accounts(self):
        session = DbSession()
        accounts = session.query(Account).all()
        self.accounts_table.setRowCount(len(accounts))
        for i, acc in enumerate(accounts):
            self.accounts_table.setItem(i, 0, QTableWidgetItem(acc.phone))
            self.accounts_table.setItem(i, 1, QTableWidgetItem("نعم" if acc.is_primary else "لا"))
            self.accounts_table.setItem(i, 2, QTableWidgetItem("نشط" if acc.is_active else "معطل"))
            channels_count = session.query(Channel).filter(Channel.account_id == acc.id).count()
            self.accounts_table.setItem(i, 3, QTableWidgetItem(str(channels_count)))
        session.close()

    def refresh_channels(self):
        self.channels_tree.clear()
        session = DbSession()
        primary_account = session.query(Account).filter(Account.is_primary == True).first()
        if not primary_account:
            self.event_log.append("لا يوجد حساب رئيسي، يرجى إضافة حساب وتحديده كرئيسي.")
            session.close()
            return
        channels = session.query(Channel).filter(Channel.account_id == primary_account.id).all()
        for ch in channels:
            item = QTreeWidgetItem([ch.title or "", ch.username or "", "✓" if ch.is_monitored else ""])
            item.setCheckState(2, Qt.Checked if ch.is_monitored else Qt.Unchecked)
            item.setData(0, Qt.UserRole, ch.id)
            self.channels_tree.addTopLevelItem(item)
        session.close()

    def refresh_stats(self):
        session = DbSession()
        accounts_count = session.query(Account).count()
        channels_count = session.query(Channel).filter(Channel.is_monitored == True).count()
        today = datetime.utcnow().replace(hour=0, minute=0, second=0)
        posts_today = session.query(Post).filter(Post.received_at >= today).count()
        urgent_today = session.query(Post).filter(Post.received_at >= today, Post.is_urgent == True).count()
        self.lbl_accounts.setText(f"الحسابات: {accounts_count}")
        self.lbl_channels.setText(f"القنوات المراقبة: {channels_count}")
        self.lbl_posts_today.setText(f"المنشورات اليوم: {posts_today}")
        self.lbl_urgent.setText(f"عاجل اليوم: {urgent_today}")
        session.close()

    def refresh_destinations(self):
        session = DbSession()
        dests = session.query(Destination).all()
        self.destinations_list.clear()
        for d in dests:
            self.destinations_list.addItem(f"{d.name} ({d.type}: {d.identifier}) - {'نشط' if d.is_active else 'معطل'} - طريقة: {d.send_method}")
        session.close()

    def refresh_keywords(self):
        session = DbSession()
        kws = session.query(Keyword).all()
        self.keywords_list.clear()
        for kw in kws:
            self.keywords_list.addItem(f"{kw.text} ({kw.language}) - {'تضمين' if kw.is_include else 'استبعاد'} - أولوية {kw.priority}")
        session.close()

    # دوال التحكم في القنوات
    @asyncSlot()
    async def sync_channels(self):
        primary = await self.telegram_manager.get_primary_account()
        if not primary:
            QMessageBox.warning(self, "خطأ", "لا يوجد حساب رئيسي، أضف حسابًا أولاً.")
            return
        self.status_label.setText("جاري جلب القنوات...")
        QApplication.processEvents()
        try:
            channels = await self.telegram_manager.get_channels_for_account(primary)
            session = DbSession()
            acc_db = session.query(Account).filter(Account.phone == primary.phone).first()
            if not acc_db:
                QMessageBox.critical(self, "خطأ", "الحساب الرئيسي غير موجود في قاعدة البيانات.")
                session.close()
                return
            for ch in channels:
                existing = session.query(Channel).filter(Channel.telegram_id == ch.id).first()
                if existing:
                    existing.title = ch.title
                    existing.username = ch.username
                else:
                    new_ch = Channel(
                        telegram_id=ch.id,
                        title=ch.title,
                        username=ch.username,
                        account_id=acc_db.id,
                        is_monitored=False
                    )
                    session.add(new_ch)
            session.commit()
            session.close()
            self.refresh_channels()
            self.event_log.append("تم جلب القنوات بنجاح.")
        except Exception as e:
            self.event_log.append(f"خطأ في جلب القنوات: {e}")
        finally:
            self.status_label.setText("جاهز")

    def select_all_channels(self):
        for i in range(self.channels_tree.topLevelItemCount()):
            item = self.channels_tree.topLevelItem(i)
            item.setCheckState(2, Qt.Checked)

    def deselect_all_channels(self):
        for i in range(self.channels_tree.topLevelItemCount()):
            item = self.channels_tree.topLevelItem(i)
            item.setCheckState(2, Qt.Unchecked)

    def save_channel_selection(self):
        session = DbSession()
        for i in range(self.channels_tree.topLevelItemCount()):
            item = self.channels_tree.topLevelItem(i)
            channel_id = item.data(0, Qt.UserRole)
            is_checked = item.checkState(2) == Qt.Checked
            channel = session.query(Channel).filter(Channel.id == channel_id).first()
            if channel:
                channel.is_monitored = is_checked
        session.commit()
        session.close()
        self.event_log.append("تم حفظ اختيارات القنوات.")
        self.refresh_stats()

    # دوال إدارة الحسابات
    def add_account_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة حساب تيليجرام")
        layout = QVBoxLayout()
        phone_edit = QLineEdit()
        phone_edit.setPlaceholderText("رقم الهاتف مع رمز الدولة (مثال: +1234567890)")
        layout.addWidget(phone_edit)
        cb_primary = QCheckBox("تعيين كحساب رئيسي (لجلب القنوات)")
        layout.addWidget(cb_primary)
        btn_add = QPushButton("إضافة")
        layout.addWidget(btn_add)
        dialog.setLayout(layout)
        btn_add.clicked.connect(lambda: self.add_account(phone_edit.text(), cb_primary.isChecked(), dialog))
        dialog.exec_()

    def add_account(self, phone: str, is_primary: bool, dialog):
        if not phone:
            QMessageBox.warning(self, "خطأ", "يرجى إدخال رقم الهاتف.")
            return
        session_name = f"session_{phone.replace('+', '').replace(' ', '')}"
        asyncio.create_task(self._add_account_async(phone, session_name, is_primary, dialog))

    async def _add_account_async(self, phone, session_name, is_primary, dialog):
        try:
            if is_primary:
                async with DbSession() as db:
                    await db.execute("UPDATE accounts SET is_primary = 0 WHERE is_primary = 1")
                    await db.commit()
            success = await self.telegram_manager.add_account(phone, session_name, is_primary)
            if success:
                self.event_log.append(f"تم إضافة الحساب {phone} بنجاح.")
                self.refresh_accounts()
                if is_primary:
                    await self.sync_channels()
                dialog.accept()
            else:
                QMessageBox.critical(self, "خطأ", "فشل في إضافة الحساب.")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"خطأ: {e}")

    # دوال إدارة الوجهات
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

    # دوال إدارة الكلمات المفتاحية
    def add_keyword_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("إضافة كلمة مفتاحية")
        layout = QFormLayout()
        text_edit = QLineEdit()
        layout.addRow("الكلمة:", text_edit)
        lang_combo = QComboBox()
        lang_combo.addItems(["ar", "en", "fa", "he", "ku", "tr", "fr"])
        layout.addRow("اللغة:", lang_combo)
        priority_spin = QSpinBox()
        priority_spin.setRange(1, 10)
        layout.addRow("الأولوية (1-10):", priority_spin)
        cb_include = QCheckBox("تضمين (إذا لم يُحدد، ستكون استبعاد)")
        cb_include.setChecked(True)
        layout.addRow(cb_include)
        btn_save = QPushButton("حفظ")
        layout.addRow(btn_save)
        dialog.setLayout(layout)

        def save():
            kw_text = text_edit.text().strip()
            if not kw_text:
                QMessageBox.warning(dialog, "خطأ", "أدخل الكلمة")
                return
            session = DbSession()
            kw = Keyword(text=kw_text, language=lang_combo.currentText(), priority=priority_spin.value(), is_include=cb_include.isChecked())
            session.add(kw)
            session.commit()
            session.close()
            self.refresh_keywords()
            dialog.accept()
        btn_save.clicked.connect(save)
        dialog.exec_()

    # معالج المنشورات الجديدة (الجزء الأساسي)
    @asyncSlot()
    async def on_new_message(self, account, message, channel):
        if not channel.is_monitored:
            return

        # حفظ المنشور
        session = DbSession()
        post = Post(
            message_id=message.id,
            channel_id=channel.id,
            account_id=channel.account_id,
            source_username=channel.username,
            text=message.text or message.caption or "",
            media_type=self._get_media_type(message),
            media_group_id=message.media_group_id if message.media_group_id else None,
            received_at=datetime.utcnow()
        )
        session.add(post)
        session.commit()
        post_id = post.id
        session.close()

        # الذكاء الاصطناعي
        if self.ai_check.isChecked():
            importance, urgent, category = await ai_engine.evaluate_importance(post.text)
            post.ai_importance = importance
            post.is_urgent = urgent
            post.ai_category = category
            summary = await ai_engine.summarize(post.text)
            session = DbSession()
            recent_texts = [p.text for p in session.query(Post).filter(Post.id != post_id).order_by(Post.received_at.desc()).limit(100) if p.text]
            duplicate_group = await ai_engine.detect_duplicate(post.text, recent_texts)
            if duplicate_group:
                post.is_duplicate = True
                post.duplicate_group = duplicate_group
            session.merge(post)
            session.commit()
            session.close()

        # الترجمة
        if self.translate_check.isChecked() and post.text:
            translated = await translator.translate(post.text)
            post.translated_text = translated
            session = DbSession()
            session.merge(post)
            session.commit()
            session.close()

        # التوجيه والإرسال
        await rules_engine.load_keywords()
        evaluation = await rules_engine.evaluate_post(post, post.text)
        if evaluation["should_send"]:
            session = DbSession()
            destinations = session.query(Destination).filter(Destination.is_active == True).all()
            session.close()
            destinations_to_send = await rules_engine.route_to_destinations(post, evaluation, destinations)
            
            # إرسال إلى الوجهات باستخدام التحويل المباشر
            for dest in destinations_to_send:
                success = await rules_engine.send_to_destination(
                    dest, post,
                    from_chat_id=channel.telegram_id,
                    message_id=message.id
                )
                if not success:
                    self.event_log.append(f"فشل إرسال إلى {dest.name}")

        # إضافة إلى القوائم المباشرة
        self.add_post_to_lists(post, channel)

    def _get_media_type(self, message):
        if message.photo:
            return "photo"
        elif message.video:
            return "video"
        elif message.media_group_id:
            return "album"
        return "none"

    def add_post_to_lists(self, post, channel):
        display_text = f"{channel.title or channel.username} | {post.text[:100]}..."
        if post.translated_text:
            display_text += f"\nترجمة: {post.translated_text[:100]}..."
        self.live_list.addItem(display_text)
        self.live_list.scrollToBottom()
        if post.media_type in ["photo", "video"]:
            self.media_list.addItem(display_text)
            self.media_list.scrollToBottom()
        if post.text and len(post.text) > 0:
            self.text_list.addItem(display_text)
            self.text_list.scrollToBottom()

    def show_post_details(self, item):
        QMessageBox.information(self, "تفاصيل", f"تفاصيل المنشور:\n{item.text()}\n\n(يمكن تطوير البحث عن المنشور الكامل)")

    def reset_settings(self):
        self.ai_check.setChecked(True)
        self.translate_check.setChecked(True)
        session = DbSession()
        session.query(Keyword).delete()
        session.commit()
        session.close()
        self.refresh_keywords()
        self.event_log.append("تمت إعادة ضبط الإعدادات الافتراضية.")

    @asyncClose
    async def closeEvent(self, event):
        await self.telegram_manager.stop_all()
        event.accept()

def run_gui():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    window = MainWindow()
    window.show()
    with loop:
        loop.run_forever()

if __name__ == "__main__":
    run_gui()
