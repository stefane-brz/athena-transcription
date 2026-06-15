import sys
import os
import datetime
import sqlite3

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    bundled_hf = os.path.join(sys._MEIPASS, 'hf_home')
    if os.path.isdir(bundled_hf):
        os.environ['HF_HOME'] = bundled_hf
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, 
    QListWidget, QListWidgetItem, QPushButton, QLabel, 
    QFileDialog, QFrame, QStackedWidget, QTextEdit, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from transcription import transcript_generator

DB_DIR = os.path.join(os.path.expanduser("~"), ".athena_transcription")
DB_PATH = os.path.join(DB_DIR, "transcriptions.db")

def get_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT,
            created_at TEXT NOT NULL,
            text TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


class TranscriptionWorker(QThread):
    progress = pyqtSignal(int, int, str)
    chunk_finished = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, filepath, model_name="small"):
        super().__init__()
        self.filepath = filepath
        self.model_name = model_name
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.progress.emit(0, 0, "Chargement du modèle Whisper...")
            generator = transcript_generator(self.filepath, mode=self.model_name, chunk_size_seconds=300)
            
            texte_complet = ""
            for current, total, texte_tranche in generator:
                if self._is_cancelled:
                    break
                self.progress.emit(current, total, f"Transcription : Tranche {current}/{total}...")
                self.chunk_finished.emit(texte_tranche)
                texte_complet += texte_tranche + " "
                
            self.finished.emit(texte_complet.strip())
        except Exception as e:
            self.error.emit(str(e))


class ApplicationHUG(QWidget):
    def __init__(self):
        super().__init__()
        self.mode_nuit = True
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("AthenaT")
        self.resize(1280, 720)
        
        layout_principal = QHBoxLayout()
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)
        
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(260)
        
        layout_sidebar = QVBoxLayout(self.sidebar)
        layout_sidebar.setContentsMargins(15, 20, 15, 20)
        
        self.btn_nouvelle_disc = QPushButton("  +  Nouvelle discussion")
        self.btn_nouvelle_disc.setCursor(Qt.PointingHandCursor)
        self.btn_nouvelle_disc.clicked.connect(self.reinitialiser_accueil)
        layout_sidebar.addWidget(self.btn_nouvelle_disc)
        
        label_recent = QLabel("Récentes")
        label_recent.setStyleSheet("color: #969696; font-weight: bold; font-size: 12px; margin-bottom: 8px;")
        layout_sidebar.addWidget(label_recent)
        
        self.liste_historique = QListWidget()
        self.liste_historique.itemClicked.connect(self.charger_discussion_selectionnee)
        layout_sidebar.addWidget(self.liste_historique)
        
        self.zone_droite = QFrame()
        
        layout_droite = QVBoxLayout(self.zone_droite)
        layout_droite.setContentsMargins(0, 0, 0, 0)
        
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent;")
        layout_droite.addWidget(self.stacked_widget)
        
        self.page_accueil = QWidget()
        self.page_accueil.setStyleSheet("background: transparent;")
        layout_accueil = QVBoxLayout(self.page_accueil)
        layout_accueil.setAlignment(Qt.AlignCenter)
        
        self.label_accueil = QLabel("Athena Transcription")
        self.label_accueil.setAlignment(Qt.AlignCenter)
        layout_accueil.addWidget(self.label_accueil)
        
        self.barre_action = QFrame()
        self.barre_action.setFixedWidth(600)
        self.barre_action.setFixedHeight(54)
        
        layout_barre = QHBoxLayout(self.barre_action)
        layout_barre.setContentsMargins(20, 0, 20, 0)
        
        self.bouton_plus = QPushButton("+")
        self.bouton_plus.setCursor(Qt.PointingHandCursor)
        self.bouton_plus.clicked.connect(self.importer_audio)
        layout_barre.addWidget(self.bouton_plus)
        
        self.label_fichier = QLabel("Importer un fichier audio...")
        layout_barre.addWidget(self.label_fichier)
        
        layout_barre.addStretch()
        
        self.bouton_envoyer = QPushButton("Envoyer")
        self.bouton_envoyer.setEnabled(False)
        self.bouton_envoyer.setCursor(Qt.PointingHandCursor)
        self.bouton_envoyer.clicked.connect(self.lancer_transcription)
        layout_barre.addWidget(self.bouton_envoyer)
        
        layout_accueil.addWidget(self.barre_action)
        
        self.label_statut = QLabel("")
        self.label_statut.setAlignment(Qt.AlignCenter)
        layout_accueil.addWidget(self.label_statut)
        
        self.stacked_widget.addWidget(self.page_accueil)
        
        self.page_discussion = QWidget()
        self.page_discussion.setStyleSheet("background: transparent;")
        layout_discussion = QVBoxLayout(self.page_discussion)
        layout_discussion.setContentsMargins(40, 40, 40, 40)
        layout_discussion.setSpacing(20)
        
        layout_entete = QHBoxLayout()
        
        self.label_titre_disc = QLabel("Nom de la discussion")
        layout_entete.addWidget(self.label_titre_disc)
        
        layout_entete.addStretch()
        
        self.bouton_annuler = QPushButton("Annuler")
        self.bouton_annuler.setCursor(Qt.PointingHandCursor)
        self.bouton_annuler.clicked.connect(self.annuler_transcription)
        self.bouton_annuler.setVisible(False)
        layout_entete.addWidget(self.bouton_annuler)
        
        self.bouton_copier = QPushButton("Copier")
        self.bouton_copier.setCursor(Qt.PointingHandCursor)
        self.bouton_copier.clicked.connect(self.copier_transcription)
        layout_entete.addWidget(self.bouton_copier)
        
        self.bouton_supprimer = QPushButton("Supprimer")
        self.bouton_supprimer.setCursor(Qt.PointingHandCursor)
        self.bouton_supprimer.clicked.connect(self.supprimer_discussion)
        layout_entete.addWidget(self.bouton_supprimer)
        
        layout_discussion.addLayout(layout_entete)
        
        self.label_info_disc = QLabel("Transcrit le ...")
        layout_discussion.addWidget(self.label_info_disc)
        
        self.label_statut_disc = QLabel("")
        layout_discussion.addWidget(self.label_statut_disc)
        
        self.texte_transcription = QTextEdit()
        self.texte_transcription.setReadOnly(True)
        layout_discussion.addWidget(self.texte_transcription)
        
        self.stacked_widget.addWidget(self.page_discussion)
        
        layout_principal.addWidget(self.sidebar)
        layout_principal.addWidget(self.zone_droite)
        self.setLayout(layout_principal)
        
        self.bouton_theme = QPushButton("", self)
        self.bouton_theme.setCursor(Qt.PointingHandCursor)
        self.bouton_theme.setFixedSize(40, 40)
        self.bouton_theme.clicked.connect(self.basculer_theme)
        
        self.chemin_fichier = None
        self.discussion_active_id = None
        self.appliquer_theme()
        
        self.charger_historique()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.bouton_theme.move(self.width() - 60, self.height() - 60)

    def basculer_theme(self):
        self.mode_nuit = not self.mode_nuit
        self.appliquer_theme()

    def appliquer_theme(self):
        if self.mode_nuit:
            self.bouton_theme.setText("☀️")
            self.bouton_theme.setStyleSheet("""
                QPushButton {
                    background-color: #1e1e20;
                    color: #e3e3e3;
                    border: 1px solid #3c4043;
                    border-radius: 20px;
                    font-size: 18px;
                }
                QPushButton:hover { background-color: #2d2f31; }
            """)
            
            self.setStyleSheet("QWidget { color: #e3e3e3; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }")
            self.sidebar.setStyleSheet("QFrame { background-color: #131314; border-right: 1px solid #1e1e20; }")
            
            self.btn_nouvelle_disc.setStyleSheet("""
                QPushButton {
                    background-color: #1e1e20;
                    border: none;
                    border-radius: 20px;
                    padding: 12px;
                    text-align: left;
                    font-weight: 500;
                    font-size: 14px;
                    margin-bottom: 20px;
                    color: #e3e3e3;
                }
                QPushButton:hover { background-color: #2d2f31; }
            """)
            
            self.liste_historique.setStyleSheet("""
                QListWidget { background-color: transparent; border: none; }
                QListWidget::item { padding: 10px; border-radius: 6px; margin-bottom: 4px; font-size: 13px; color: #e3e3e3; }
                QListWidget::item:hover { background-color: #1e1e20; }
                QListWidget::item:selected { background-color: #004a77; color: #c2e7ff; }
            """)
            
            self.zone_droite.setStyleSheet("""
                QFrame {
                    background-color: qradialgradient(
                        cx: 0.5, cy: 0.6, radius: 0.7,
                        fx: 0.5, fy: 0.6,
                        stop: 0 #111a2e, 
                        stop: 0.6 #090a0f,
                        stop: 1 #000000
                    );
                }
            """)
            
            self.label_accueil.setStyleSheet("background-color: transparent; color: #e3e3e3; font-size: 40px; font-weight: 400; margin-bottom: 35px;")
            
            self.barre_action.setStyleSheet("""
                QFrame { background-color: #1e1e20; border: 1px solid #3c4043; border-radius: 27px; }
                QFrame:hover { border-color: #5f6368; background-color: #242426; }
            """)
            
            self.bouton_plus.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #a8c7fa;
                    font-size: 26px;
                    font-weight: 300;
                    border: none;
                    text-align: left;
                }
                QPushButton:hover { color: #c2e7ff; }
            """)
            
            self.label_fichier.setStyleSheet(f"color: {'#e3e3e3' if self.chemin_fichier else '#969696'}; font-size: 14px; background-color: transparent; margin-left: 10px;")
            
            self.bouton_envoyer.setStyleSheet("""
                QPushButton {
                    background-color: #2d2f31;
                    color: #969696;
                    border: none;
                    border-radius: 15px;
                    padding: 6px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:enabled { background-color: #004a77; color: #c2e7ff; }
                QPushButton:enabled:hover { background-color: #005a91; }
            """)
            
            self.label_statut.setStyleSheet("background-color: transparent; color: #a8c7fa; font-size: 13px; margin-top: 15px;")
            
            self.label_titre_disc.setStyleSheet("color: #e3e3e3; font-size: 24px; font-weight: bold; background: transparent;")
            self.label_info_disc.setStyleSheet("color: #969696; font-size: 12px; background: transparent;")
            self.label_statut_disc.setStyleSheet("color: #a8c7fa; font-weight: bold; font-size: 13px; background: transparent;")
            
            self.bouton_annuler.setStyleSheet("""
                QPushButton {
                    background-color: #3c2626;
                    color: #f28b82;
                    border: 1px solid #f28b82;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #4e3030; }
            """)
            
            self.bouton_copier.setStyleSheet("""
                QPushButton {
                    background-color: #1e1e20;
                    color: #a8c7fa;
                    border: 1px solid #3c4043;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #2d2f31; border-color: #5f6368; }
            """)
            
            self.bouton_supprimer.setStyleSheet("""
                QPushButton {
                    background-color: #1e1e20;
                    color: #f28b82;
                    border: 1px solid #3c4043;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #3c2626; border-color: #f28b82; }
            """)
            
            self.texte_transcription.setStyleSheet("""
                QTextEdit {
                    background-color: #131314;
                    color: #e3e3e3;
                    border: 1px solid #1e1e20;
                    border-radius: 12px;
                    padding: 20px;
                    font-size: 15px;
                }
            """)
        else:
            self.bouton_theme.setText("🌙")
            self.bouton_theme.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #1f1f1f;
                    border: 1px solid #dadada;
                    border-radius: 20px;
                    font-size: 18px;
                }
                QPushButton:hover { background-color: #f5f5f5; }
            """)
            
            self.setStyleSheet("QWidget { color: #1f1f1f; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; }")
            self.sidebar.setStyleSheet("QFrame { background-color: #f6f3ea; border-right: 1px solid #e2ded4; }")
            
            self.btn_nouvelle_disc.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #dadada;
                    border-radius: 20px;
                    padding: 12px;
                    text-align: left;
                    font-weight: 500;
                    font-size: 14px;
                    margin-bottom: 20px;
                    color: #1f1f1f;
                }
                QPushButton:hover { background-color: #f5f5f5; }
            """)
            
            self.liste_historique.setStyleSheet("""
                QListWidget { background-color: transparent; border: none; }
                QListWidget::item { padding: 10px; border-radius: 6px; margin-bottom: 4px; font-size: 13px; color: #1f1f1f; }
                QListWidget::item:hover { background-color: #edeae0; }
                QListWidget::item:selected { background-color: #c2e7ff; color: #004a77; }
            """)
            
            self.zone_droite.setStyleSheet("""
                QFrame {
                    background-color: qradialgradient(
                        cx: 0.5, cy: 0.6, radius: 0.7,
                        fx: 0.5, fy: 0.6,
                        stop: 0 #faf8f3, 
                        stop: 0.6 #f5f2e9,
                        stop: 1 #ede9dd
                    );
                }
            """)
            
            self.label_accueil.setStyleSheet("background-color: transparent; color: #1f1f1f; font-size: 40px; font-weight: 400; margin-bottom: 35px;")
            
            self.barre_action.setStyleSheet("""
                QFrame { background-color: #ffffff; border: 1px solid #dadada; border-radius: 27px; }
                QFrame:hover { border-color: #b0b0b0; }
            """)
            
            self.bouton_plus.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #004a77;
                    font-size: 26px;
                    font-weight: 300;
                    border: none;
                    text-align: left;
                }
                QPushButton:hover { color: #005a91; }
            """)
            
            self.label_fichier.setStyleSheet(f"color: {'#1f1f1f' if self.chemin_fichier else '#767676'}; font-size: 14px; background-color: transparent; margin-left: 10px;")
            
            self.bouton_envoyer.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    color: #9e9e9e;
                    border: none;
                    border-radius: 15px;
                    padding: 6px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:enabled { background-color: #c2e7ff; color: #004a77; }
                QPushButton:enabled:hover { background-color: #a2d7ff; }
            """)
            
            self.label_statut.setStyleSheet("background-color: transparent; color: #004a77; font-size: 13px; margin-top: 15px;")
            
            self.label_titre_disc.setStyleSheet("color: #1f1f1f; font-size: 24px; font-weight: bold; background: transparent;")
            self.label_info_disc.setStyleSheet("color: #5f6368; font-size: 12px; background: transparent;")
            self.label_statut_disc.setStyleSheet("color: #004a77; font-weight: bold; font-size: 13px; background: transparent;")
            
            self.bouton_annuler.setStyleSheet("""
                QPushButton {
                    background-color: #ffebee;
                    color: #c62828;
                    border: 1px solid #c62828;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #ffcdd2; }
            """)
            
            self.bouton_copier.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #004a77;
                    border: 1px solid #dadada;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #f5f5f5; border-color: #b0b0b0; }
            """)
            
            self.bouton_supprimer.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #c62828;
                    border: 1px solid #dadada;
                    border-radius: 15px;
                    padding: 6px 15px;
                    font-weight: 500;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #ffebee; border-color: #c62828; }
            """)
            
            self.texte_transcription.setStyleSheet("""
                QTextEdit {
                    background-color: #ffffff;
                    color: #1f1f1f;
                    border: 1px solid #e2ded4;
                    border-radius: 12px;
                    padding: 20px;
                    font-size: 15px;
                }
            """)

    def afficher_confirmation(self, titre, texte):
        msg = QMessageBox(self)
        msg.setWindowTitle(titre)
        msg.setText(texte)
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if self.mode_nuit:
            msg.setStyleSheet("""
                QMessageBox { background-color: #131314; }
                QLabel { color: #e3e3e3; font-size: 14px; }
                QPushButton {
                    background-color: #1e1e20;
                    color: #e3e3e3;
                    border: 1px solid #3c4043;
                    border-radius: 6px;
                    padding: 5px 15px;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #2d2f31; }
            """)
        else:
            msg.setStyleSheet("""
                QMessageBox { background-color: #faf8f3; }
                QLabel { color: #1f1f1f; font-size: 14px; }
                QPushButton {
                    background-color: #ffffff;
                    color: #1f1f1f;
                    border: 1px solid #dadada;
                    border-radius: 6px;
                    padding: 5px 15px;
                    font-size: 13px;
                }
                QPushButton:hover { background-color: #f5f5f5; }
            """)
            
        return msg.exec_() == QMessageBox.Yes

    def reinitialiser_accueil(self):
        self.liste_historique.clearSelection()
        self.chemin_fichier = None
        self.discussion_active_id = None
        
        self.label_fichier.setText("Importer un fichier audio...")
        self.label_statut.setText("")
        self.appliquer_theme()
        
        self.stacked_widget.setCurrentIndex(0)

    def importer_audio(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            return
            
        options = QFileDialog.Options()
        fichier, _ = QFileDialog.getOpenFileName(
            self, 
            "Déposer un fichier audio", 
            "", 
            "Fichiers Audio (*.mp3 *.wav *.m4a *.flac);;Tous les fichiers (*)", 
            options=options
        )
        
        if fichier:
            self.chemin_fichier = fichier
            nom_fichier = fichier.split("/")[-1]
            self.label_fichier.setText(nom_fichier)
            self.bouton_envoyer.setEnabled(True)
            self.label_statut.setText("")
            self.appliquer_theme()

    def lancer_transcription(self):
        if not self.chemin_fichier:
            return
            
        self.bouton_plus.setEnabled(False)
        self.bouton_envoyer.setEnabled(False)
        self.btn_nouvelle_disc.setEnabled(False)
        self.liste_historique.setEnabled(False)
        
        nom_fichier = self.chemin_fichier.split("/")[-1]
        
        conn = get_db()
        try:
            cursor = conn.execute(
                "INSERT INTO transcriptions (title, filename, filepath, created_at, text) VALUES (?, ?, ?, ?, ?)",
                (nom_fichier, nom_fichier, self.chemin_fichier,
                 datetime.datetime.now(datetime.timezone.utc).isoformat(), "")
            )
            conn.commit()
            self.discussion_active_id = cursor.lastrowid
            
            self.label_titre_disc.setText(nom_fichier)
            self.label_info_disc.setText(f"Fichier : {nom_fichier} • Transcrit le {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}")
            self.label_statut_disc.setText("Initialisation de Whisper...")
            self.texte_transcription.clear()
            
            self.bouton_annuler.setVisible(True)
            self.bouton_copier.setVisible(False)
            self.bouton_supprimer.setVisible(False)
            
            self.stacked_widget.setCurrentIndex(1)
            
            self.charger_historique_silencieux()
            
            self.worker = TranscriptionWorker(self.chemin_fichier)
            self.worker.progress.connect(self.on_transcription_progres)
            self.worker.chunk_finished.connect(self.on_tranche_terminee)
            self.worker.finished.connect(self.on_transcription_succes)
            self.worker.error.connect(self.on_transcription_erreur)
            self.worker.start()
        except Exception as e:
            self.label_statut.setText(f"⚠️ Erreur d'initialisation : {str(e)}")
            self.bouton_plus.setEnabled(True)
            self.btn_nouvelle_disc.setEnabled(True)
            self.liste_historique.setEnabled(True)
            self.bouton_envoyer.setEnabled(True)
        finally:
            conn.close()

    def annuler_transcription(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            reply = self.afficher_confirmation("Annuler la transcription", "Voulez-vous vraiment annuler la transcription en cours ?")
            if reply:
                self.worker.cancel()
                self.worker.wait()
                
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                
                self.bouton_annuler.setVisible(False)
                self.bouton_copier.setVisible(True)
                self.bouton_supprimer.setVisible(True)
                
                self.bouton_plus.setEnabled(True)
                self.btn_nouvelle_disc.setEnabled(True)
                self.liste_historique.setEnabled(True)
                self.bouton_envoyer.setEnabled(True)
                
                self.label_statut_disc.setText("⏹️ Transcription annulée")
                self.label_statut.setText("")
                
                self.charger_historique()

    def on_transcription_progres(self, current, total, message):
        self.label_statut.setText(message)
        self.label_statut_disc.setText(message)

    def on_tranche_terminee(self, texte_tranche):
        if not texte_tranche.strip():
            return
            
        curseur = self.texte_transcription.textCursor()
        curseur.movePosition(curseur.End)
        self.texte_transcription.setTextCursor(curseur)
        self.texte_transcription.insertPlainText(texte_tranche)
        
        texte_complet = self.texte_transcription.toPlainText()
        conn = get_db()
        try:
            conn.execute(
                "UPDATE transcriptions SET text = ? WHERE id = ?",
                (texte_complet, self.discussion_active_id)
            )
            conn.commit()
        except Exception as e:
            print("Erreur de sauvegarde progressive :", e)
        finally:
            conn.close()

    def on_transcription_succes(self, texte_final):
        self.label_statut_disc.setText("✅ Transcription terminée !")
        self.label_statut.setText("✅ Transcription terminée !")
        
        self.bouton_annuler.setVisible(False)
        self.bouton_copier.setVisible(True)
        self.bouton_supprimer.setVisible(True)
        
        self.bouton_plus.setEnabled(True)
        self.btn_nouvelle_disc.setEnabled(True)
        self.liste_historique.setEnabled(True)
        
        self.chemin_fichier = None
        self.label_fichier.setText("Importer un fichier audio...")
        self.bouton_envoyer.setEnabled(False)
        self.appliquer_theme()
        
        self.charger_historique_silencieux()

    def on_transcription_erreur(self, err_msg):
        self.label_statut_disc.setText(f"❌ Erreur : {err_msg}")
        self.label_statut.setText(f"❌ Erreur : {err_msg}")
        
        self.bouton_annuler.setVisible(False)
        self.bouton_copier.setVisible(True)
        self.bouton_supprimer.setVisible(True)
        
        self.bouton_plus.setEnabled(True)
        self.btn_nouvelle_disc.setEnabled(True)
        self.liste_historique.setEnabled(True)
        self.bouton_envoyer.setEnabled(True)

    def charger_historique(self):
        self.liste_historique.clear()
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, title, filename, created_at FROM transcriptions ORDER BY created_at DESC"
            ).fetchall()
            for row in rows:
                item = QListWidgetItem(row["title"])
                item.setData(Qt.UserRole, row["id"])
                self.liste_historique.addItem(item)
        except Exception as e:
            print("Erreur lors du chargement de l'historique :", e)
            self.label_statut.setText("⚠️ Impossible de charger l'historique.")
        finally:
            conn.close()

    def charger_historique_silencieux(self):
        self.liste_historique.blockSignals(True)
        self.liste_historique.clear()
        conn = get_db()
        try:
            rows = conn.execute(
                "SELECT id, title, filename, created_at FROM transcriptions ORDER BY created_at DESC"
            ).fetchall()
            for row in rows:
                item = QListWidgetItem(row["title"])
                item.setData(Qt.UserRole, row["id"])
                self.liste_historique.addItem(item)
                if row["id"] == self.discussion_active_id:
                    self.liste_historique.setCurrentItem(item)
        except Exception as e:
            print("Erreur historique silencieux :", e)
        finally:
            conn.close()
        self.liste_historique.blockSignals(False)

    def charger_discussion_selectionnee(self, item):
        doc_id = item.data(Qt.UserRole)
        if doc_id is not None:
            self.charger_discussion(doc_id)

    def charger_discussion(self, doc_id):
        conn = get_db()
        try:
            row = conn.execute(
                "SELECT * FROM transcriptions WHERE id = ?", (doc_id,)
            ).fetchone()
            if row:
                self.discussion_active_id = row["id"]
                self.label_titre_disc.setText(row["title"])
                
                created_at_str = row["created_at"]
                if created_at_str:
                    try:
                        dt = datetime.datetime.fromisoformat(created_at_str)
                        date_str = dt.strftime("%d/%m/%Y à %H:%M")
                    except ValueError:
                        date_str = created_at_str
                else:
                    date_str = "Date inconnue"
                    
                self.label_info_disc.setText(f"Fichier : {row['filename']} • Transcrit le {date_str}")
                self.label_statut_disc.setText("")
                
                self.bouton_annuler.setVisible(False)
                self.bouton_copier.setVisible(True)
                self.bouton_supprimer.setVisible(True)
                
                self.texte_transcription.setHtml(f"<div style='line-height: 1.6; font-size: 15px;'>{row['text']}</div>")
                
                self.stacked_widget.setCurrentIndex(1)
        except Exception as e:
            self.label_statut.setText(f"⚠️ Erreur de lecture : {str(e)}")
        finally:
            conn.close()

    def copier_transcription(self):
        texte = self.texte_transcription.toPlainText()
        if texte:
            QApplication.clipboard().setText(texte)
            self.bouton_copier.setText("Copié !")
            QTimer.singleShot(2000, lambda: self.bouton_copier.setText("Copier"))

    def supprimer_discussion(self):
        if self.discussion_active_id is None:
            return
            
        reply = self.afficher_confirmation(
            "Supprimer la discussion", 
            "Voulez-vous vraiment supprimer cette discussion définitivement ?"
        )
        
        if reply:
            conn = get_db()
            try:
                conn.execute(
                    "DELETE FROM transcriptions WHERE id = ?",
                    (self.discussion_active_id,)
                )
                conn.commit()
                self.reinitialiser_accueil()
                self.charger_historique()
            except Exception as e:
                msg = QMessageBox(self)
                msg.setWindowTitle("Erreur")
                msg.setText(f"Erreur lors de la suppression : {str(e)}")
                if self.mode_nuit:
                    msg.setStyleSheet("QMessageBox { background-color: #131314; } QLabel { color: #e3e3e3; } QPushButton { background-color: #1e1e20; color: #e3e3e3; }")
                else:
                    msg.setStyleSheet("QMessageBox { background-color: #faf8f3; } QLabel { color: #1f1f1f; } QPushButton { background-color: #ffffff; color: #1f1f1f; }")
                msg.exec_()
            finally:
                conn.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_db()
    fenetre = ApplicationHUG()
    fenetre.show()
    sys.exit(app.exec_())
