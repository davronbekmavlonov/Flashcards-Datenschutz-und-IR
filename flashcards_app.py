import sys
import sqlite3
import random
from PyQt5 import QtWidgets, QtGui, QtCore

DB_FILE = 'flashcards.db'

# Database initialization
conn = sqlite3.connect(DB_FILE)
c = conn.cursor()
c.execute('CREATE TABLE IF NOT EXISTS subjects (id INTEGER PRIMARY KEY, name TEXT UNIQUE)')
c.execute('CREATE TABLE IF NOT EXISTS topics (id INTEGER PRIMARY KEY, subject_id INTEGER, name TEXT, UNIQUE(subject_id,name))')
c.execute('CREATE TABLE IF NOT EXISTS cards (id INTEGER PRIMARY KEY, topic_id INTEGER, front TEXT, back TEXT, known INTEGER DEFAULT 0)')
conn.commit()

# Predefined pastel colors for cards
CARD_COLORS = ['#FFCDD2', '#F8BBD0', '#E1BEE7', '#D1C4E9', '#C5CAE9', '#B3E5FC', '#C8E6C9', '#FFF9C4']

class FlashcardApp(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Flashcards Study App')
        self.resize(1000, 600)
        self.setStyleSheet("""
            QMainWindow { background-color: #FFFDF6; }
            QListWidget { background-color: #F7F3F2; color: #333; border-radius: 10px; }
            QListWidget::item:selected { background-color: #FFCC80; color: #333; border-radius: 10px; }
            QPushButton { background-color: #FFB74D; color: #FFF; border: none; border-radius: 12px; padding: 8px; }
            QPushButton:hover { background-color: #FFA726; }
            QTableWidget { background-color: #FFFFFF; gridline-color: #FFD180; border-radius: 10px; }
            QHeaderView::section { background-color: #FFB74D; color: #FFF; padding: 6px; border-radius: 6px; }
            QLabel { color: #555; }
        """)
        self.central = QtWidgets.QWidget()
        self.setCentralWidget(self.central)
        self.layout = QtWidgets.QHBoxLayout(self.central)
        self.init_sidebar()
        self.init_main()
        self.load_subjects()

    def init_sidebar(self):
        sidebar = QtWidgets.QFrame()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet('background:#ECEFF1; border-top-left-radius: 12px; border-bottom-left-radius: 12px;')
        vbox = QtWidgets.QVBoxLayout(sidebar)
        vbox.setContentsMargins(12,12,12,12)
        lbl_subj = QtWidgets.QLabel('Subjects')
        lbl_subj.setFont(QtGui.QFont('Arial', 12, QtGui.QFont.Bold))
        vbox.addWidget(lbl_subj)
        self.subj_list = QtWidgets.QListWidget()
        self.subj_list.itemSelectionChanged.connect(self.on_subject_select)
        vbox.addWidget(self.subj_list)
        vbox.addWidget(self.create_button('Add Subject', self.add_subject))
        vbox.addSpacing(20)
        lbl_topic = QtWidgets.QLabel('Topics')
        lbl_topic.setFont(QtGui.QFont('Arial', 12, QtGui.QFont.Bold))
        vbox.addWidget(lbl_topic)
        self.topic_list = QtWidgets.QListWidget()
        self.topic_list.itemSelectionChanged.connect(self.on_topic_select)
        vbox.addWidget(self.topic_list)
        vbox.addWidget(self.create_button('Add Topic', self.add_topic))
        vbox.addStretch()
        btn_start = self.create_button('Start Session', self.start_session, '#FF8A65')
        vbox.addWidget(btn_start)
        self.layout.addWidget(sidebar)

    def init_main(self):
        main_area = QtWidgets.QFrame()
        main_area.setStyleSheet('background:#FFFFFF; border-top-right-radius:12px; border-bottom-right-radius:12px;')
        vbox = QtWidgets.QVBoxLayout(main_area)
        vbox.setContentsMargins(12,12,12,12)
        title = QtWidgets.QLabel('Cards')
        title.setFont(QtGui.QFont('Arial', 14, QtGui.QFont.Bold))
        vbox.addWidget(title)
        self.card_table = QtWidgets.QTableWidget(0, 3)
        self.card_table.setHorizontalHeaderLabels(['Front', 'Back', 'Known'])
        self.card_table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        vbox.addWidget(self.card_table)
        hbox = QtWidgets.QHBoxLayout()
        for text, func, color in [
            ('Add Card', self.add_card, '#A5D6A7'),
            ('Edit Card', self.edit_card, '#90CAF9'),
            ('Delete Card', self.delete_card, '#EF9A9A')]:
            hbox.addWidget(self.create_button(text, func, color))
        vbox.addLayout(hbox)
        self.layout.addWidget(main_area)

    def create_button(self, text, callback, bg='#FFB74D'):
        btn = QtWidgets.QPushButton(text)
        btn.setStyleSheet(f'background-color: {bg}; color: #FFF; border-radius: 12px; padding: 8px;')
        btn.clicked.connect(callback)
        return btn

    def load_subjects(self):
        self.subj_list.clear()
        for row in c.execute('SELECT name FROM subjects ORDER BY name'):
            self.subj_list.addItem(row[0])

    def on_subject_select(self):
        items = self.subj_list.selectedItems()
        if not items: return
        self.current_subject = c.execute('SELECT id FROM subjects WHERE name=?', (items[0].text(),)).fetchone()[0]
        self.load_topics()

    def add_subject(self):
        name, ok = QtWidgets.QInputDialog.getText(self, 'Add Subject', 'Subject name:')
        if ok and name:
            try:
                c.execute('INSERT INTO subjects(name) VALUES(?)', (name,))
                conn.commit()
                self.load_subjects()
            except sqlite3.IntegrityError:
                QtWidgets.QMessageBox.warning(self, 'Error', 'Subject already exists.')

    def load_topics(self):
        self.topic_list.clear()
        self.topic_list.addItem('_Poorly Known_')
        for row in c.execute('SELECT name FROM topics WHERE subject_id=? ORDER BY name', (self.current_subject,)):
            self.topic_list.addItem(row[0])

    def add_topic(self):
        if not self.subj_list.selectedItems(): return
        name, ok = QtWidgets.QInputDialog.getText(self, 'Add Topic', 'Topic name:')
        if ok and name:
            try:
                c.execute('INSERT INTO topics(subject_id,name) VALUES(?,?)',
                          (self.current_subject, name))
                conn.commit()
                self.load_topics()
            except sqlite3.IntegrityError:
                QtWidgets.QMessageBox.warning(self, 'Error', 'Topic already exists.')

    def on_topic_select(self):
        if not self.topic_list.selectedItems(): return
        name = self.topic_list.selectedItems()[0].text()
        if name == '_Poorly Known_':
            self.current_topic = None
            self.load_cards(poor=True)
        else:
            self.current_topic = c.execute('SELECT id FROM topics WHERE subject_id=? AND name=?',
                                           (self.current_subject, name)).fetchone()[0]
            self.load_cards()

    def load_cards(self, poor=False):
        # Fetch rows
        if poor:
            rows = c.execute('SELECT id,front,back,known FROM cards WHERE known=0 AND topic_id IN '
                             '(SELECT id FROM topics WHERE subject_id=?)', (self.current_subject,)).fetchall()
        else:
            rows = c.execute('SELECT id,front,back,known FROM cards WHERE topic_id=?', (self.current_topic,)).fetchall()
        # Populate table
        self.card_table.setRowCount(0)
        self.session_cards = []
        for i, (cid, front, back, known) in enumerate(rows):
            color = CARD_COLORS[i % len(CARD_COLORS)]
            self.session_cards.append((cid, front, back, color))
            row = self.card_table.rowCount()
            self.card_table.insertRow(row)
            item_f = QtWidgets.QTableWidgetItem(front)
            item_b = QtWidgets.QTableWidgetItem(back)
            item_k = QtWidgets.QTableWidgetItem('Yes' if known else 'No')
            self.card_table.setItem(row, 0, item_f)
            self.card_table.setItem(row, 1, item_b)
            self.card_table.setItem(row, 2, item_k)
        random.shuffle(self.session_cards)

    def add_card(self):
        if not self.current_topic: return
        dialog = CardDialog()
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            front, back = dialog.get_values()
            c.execute('INSERT INTO cards(topic_id,front,back) VALUES(?,?,?)',
                      (self.current_topic, front, back))
            conn.commit()
            self.load_cards()

    def edit_card(self):
        items = self.card_table.selectedItems()
        if not items: return
        idx = items[0].row()
        front = self.card_table.item(idx, 0).text()
        back = self.card_table.item(idx, 1).text()
        dialog = CardDialog(front, back)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            new_front, new_back = dialog.get_values()
            c.execute('UPDATE cards SET front=?,back=? WHERE front=? AND back=?',
                      (new_front, new_back, front, back))
            conn.commit()
            self.load_cards()

    def delete_card(self):
        items = self.card_table.selectedItems()
        if not items: return
        idx = items[0].row()
        front = self.card_table.item(idx, 0).text()
        back = self.card_table.item(idx, 1).text()
        c.execute('DELETE FROM cards WHERE front=? AND back=?', (front, back))
        conn.commit()
        self.load_cards()

    def start_session(self):
        if not hasattr(self, 'session_cards') or not self.session_cards:
            QtWidgets.QMessageBox.information(self, 'Session', 'No cards to study.')
            return
        session = StudySession(self.session_cards.copy())
        session.exec_()
        self.load_cards()

class CardDialog(QtWidgets.QDialog):
    def __init__(self, front='', back=''):
        super().__init__()
        self.setWindowTitle('Card Details')
        layout = QtWidgets.QFormLayout(self)
        self.front_edit = QtWidgets.QLineEdit(front)
        self.back_edit = QtWidgets.QLineEdit(back)
        layout.addRow('Front:', self.front_edit)
        layout.addRow('Back:', self.back_edit)
        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_values(self):
        return self.front_edit.text(), self.back_edit.text()

class StudySession(QtWidgets.QDialog):
    def __init__(self, cards):
        super().__init__()
        self.cards = cards
        self.index = 0
        self.setWindowTitle('Study Session')
        self.resize(600, 400)
        layout = QtWidgets.QVBoxLayout(self)
        self.card_frame = QtWidgets.QFrame()
        self.card_frame.setFixedSize(500, 250)
        cf_layout = QtWidgets.QVBoxLayout(self.card_frame)
        self.front_lbl = QtWidgets.QLabel('', alignment=QtCore.Qt.AlignCenter)
        self.front_lbl.setFont(QtGui.QFont('Arial', 20, QtGui.QFont.Bold))
        self.front_lbl.setWordWrap(True)
        cf_layout.addWidget(self.front_lbl)
        self.back_lbl = QtWidgets.QLabel('', alignment=QtCore.Qt.AlignCenter)
        self.back_lbl.setFont(QtGui.QFont('Arial', 16))
        self.back_lbl.setWordWrap(True)
        self.back_lbl.setStyleSheet('color: #555;')
        cf_layout.addWidget(self.back_lbl)
        layout.addWidget(self.card_frame, alignment=QtCore.Qt.AlignCenter)
        btns = QtWidgets.QHBoxLayout()
        for text, cb, col in [('Show Answer', self.flip_card, '#26A69A'), ('Know', lambda: self.mark(True), '#66BB6A'), ('Don\'t Know', lambda: self.mark(False), '#EF5350')]:
            btn = QtWidgets.QPushButton(text)
            btn.setStyleSheet(f'background-color: {col}; color: #FFF; border-radius: 12px; padding: 8px;')
            btn.clicked.connect(cb)
            btns.addWidget(btn)
        layout.addLayout(btns)
        self.show_card()

    def show_card(self):
        cid, front, back, color = self.cards[self.index]
        self.card_frame.setStyleSheet(f'background-color: {color}; border-radius: 12px;')
        self.front = front
        self.back = back
        self.front_lbl.setText(front)
        self.back_lbl.setText('')

    def flip_card(self):
        anim1 = QtCore.QPropertyAnimation(self.card_frame, b'maximumWidth')
        anim1.setDuration(200)
        anim1.setStartValue(500)
        anim1.setEndValue(0)
        anim1.finished.connect(self.on_shrink)
        anim1.start()
        self.anim1 = anim1

    def on_shrink(self):
        if self.back_lbl.text():
            self.front_lbl.setText(self.front)
            self.back_lbl.setText('')
        else:
            self.front_lbl.setText(self.front)
            self.back_lbl.setText(self.back)
        anim2 = QtCore.QPropertyAnimation(self.card_frame, b'maximumWidth')
        anim2.setDuration(200)
        anim2.setStartValue(0)
        anim2.setEndValue(500)
        anim2.start()
        self.anim2 = anim2

    def mark(self, knows):
        cid, _, _, _ = self.cards[self.index]
        c.execute('UPDATE cards SET known=? WHERE id=?', (1 if knows else 0, cid))
        conn.commit()
        self.index += 1
        if self.index >= len(self.cards):
            QtWidgets.QMessageBox.information(self, 'Session', 'Session complete!')
            self.accept()
        else:
            self.show_card()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = FlashcardApp()
    window.show()
    sys.exit(app.exec_())
