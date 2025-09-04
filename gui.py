import os
import random
import sys
from typing import List, Dict

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtMultimedia import QSoundEffect, QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFrame, \
    QSizePolicy, QComboBox, QCheckBox, QAbstractItemView, QFileDialog, QScrollArea
from PyQt6.QtGui import QMovie, QPixmap, QFont, QIcon

import processor
from settings import SoundifierSettings

CHARACTERS = {}
DEFAULT_UNIVERSES = ["Basic", "Undertale", "Deltarune"]

class BasicCharacter:
    def __init__(self, voice_paths, universe):
        self.voice_paths = voice_paths
        self.universe = universe

    def get_variant_name(self):
        return "Variant"

    def get_variant(self):
        return self

    def maybe_get_variant(self, should):
        if should:
            return self.get_variant()
        else:
            return self

class CharacterWithVariant(BasicCharacter):
    def __init__(self, voice_paths, universe, variant_name, variant_voice_paths):
        super().__init__(voice_paths, universe)
        self.variant_name = variant_name
        self.variant = BasicCharacter(variant_voice_paths, universe)

    def get_variant_name(self):
        return self.variant_name

    def get_variant(self):
        return self.variant

class TextBoxDisplayAndReceiver(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window: MainWindow = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls and len(event.mimeData().urls()) == 1 and event.mimeData().urls()[0].path().endswith(".gif"):
            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(self, event):
        path = event.mimeData().urls()[0].toLocalFile()
        print(f"Dropped in {path}")
        self.main_window.set_text_box(path)

class MainWindow(QWidget):
    settings: SoundifierSettings

    gif_path: str
    movie: QMovie
    text_box_display: QLabel

    character_dropdown: QComboBox
    universe_scroll_area: QScrollArea
    universe_checkboxes: Dict[str, QCheckBox]

    variant_label: QLabel
    variant_checkbox: QCheckBox

    add_file_button: QPushButton
    remove_file_button: QPushButton

    files: List[str]
    file_list: QListWidget

    nag_label: QLabel

    preview_button: QPushButton
    save_button: QPushButton
    save_gif_button: QPushButton

    sound: QSoundEffect
    previewing: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = SoundifierSettings(get_preview_path())

        self.sound = QSoundEffect()
        self.sound.setVolume(1.0)
        self.previewing = False

        # set the window title
        self.setWindowTitle("UTDR Text Box Soundifier")
        self.setFixedSize(766, 670)

        self.text_box_display = TextBoxDisplayAndReceiver(self)
        self.set_text_box("./assets/hint_text_box.gif")
        self.text_box_display.setScaledContents(False)

        self.config_layout = QHBoxLayout()

        voice_layout = make_config_section("Voice")

        character_layout = QHBoxLayout()

        self.character_dropdown = QComboBox(self)
        self.character_dropdown.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))

        # for name in CHARACTERS:
        #     self.character_dropdown.addItem(name)
        #     print(name + " is from universe " + CHARACTERS[name].universe)

        self.character_dropdown.activated.connect(self.change_character)

        universes_button: QPushButton = QPushButton()
        universes_button.setIcon(QIcon("./assets/universes.png"))
        universes_button.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))
        # universes_button.setFixedWidth(25)
        universes_button.setCheckable(True)
        universes_button.clicked.connect(self.configure_universes)

        character_label = QLabel("Character: ")
        character_layout.addWidget(character_label)
        character_layout.addWidget(self.character_dropdown)
        character_layout.addWidget(universes_button)

        variant_layout = QHBoxLayout()

        self.variant_label = QLabel("Variant: ")
        self.variant_label.setDisabled(True)
        self.variant_label.setHidden(True)

        self.variant_checkbox = QCheckBox()
        self.variant_checkbox.setDisabled(True)
        self.variant_checkbox.setHidden(True)
        self.variant_checkbox.clicked.connect(self.toggle_variant)

        variant_layout.addWidget(self.variant_label)
        variant_layout.addWidget(self.variant_checkbox)
        variant_layout.addStretch()

        self.universe_scroll_area = QScrollArea()
        self.universe_scroll_area.setHidden(True)

        self.load_characters(is_initial=True)

        file_manage_layout = QHBoxLayout()

        self.add_file_button = QPushButton("Add File")
        self.add_file_button.clicked.connect(self.add_file)
        self.remove_file_button = QPushButton("Remove File")
        self.remove_file_button.setDisabled(True)
        self.remove_file_button.clicked.connect(self.remove_file)

        file_manage_layout.addWidget(self.add_file_button)
        file_manage_layout.addWidget(self.remove_file_button)

        self.files = []
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.itemSelectionChanged.connect(self.select_file_from_list)

        voice_layout.addLayout(character_layout)
        voice_layout.addLayout(variant_layout)
        voice_layout.addWidget(self.universe_scroll_area)
        voice_layout.addLayout(file_manage_layout)
        voice_layout.addWidget(self.file_list)

        processing_layout = make_config_section("Processing")

        instructions_layout = make_config_section("Instructions")
        instructions_steps_label = QLabel(
        """
        <p style="text-indent:10px;">1. Use <a href="https://www.demirramon.com/generators/undertale_text_box_generator">Demirramon's Undertale Text Box Generator</a> to create an animated text box. (Make sure "Export settings>Format" is set to "Animated GIF".)</p>
        <p style="text-indent:10px;">2. Import the animated text box into the Soundifier. (Tip: You can double-click the Soundifier's text box, or drag-and-drop the gif onto it instead. You can even drag it directly from the browser!)</p>
        <p style="text-indent:10px;">3. Configure the Soundifier's voice and processing settings to your liking.</p>
        <p style="text-indent:10px;">4. Press "Preview Sound" to hear the output in sync with the preview at the top, or press "Save Sound" when you're done. If you've adjusted the "Speed" setting, you can save a sped-up or slowed-down version of the gif with "Save Sound + Gif", for convenience.</p>
        <p style="text-indent:10px;">5. Put the exported sound into the video editing software of your choice, at the same position of the timeline as the text box gif.</p>
        """
        )

        instructions_steps_label.setOpenExternalLinks(True)
        instructions_steps_label.setWordWrap(True)
        instructions_steps_label.setFixedWidth(200)
        # instructions_steps_label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred))

        instructions_scroll = QScrollArea()
        self.testscroll = instructions_scroll
        instructions_scroll.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding))
        instructions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # instructions_scroll.setWidgetResizable(True)

        instructions_scroll.setWidget(instructions_steps_label)

        links_buttons_layout = QHBoxLayout()

        links_buttons_layout.addStretch()
        links_buttons_layout.addWidget(make_link_button("ko-fi.png", "https://ko-fi.com/floralquafloral", "Button for coolest people"))
        links_buttons_layout.addWidget(make_link_button("github.png", "https://github.com/floral-qua-floral/UTDR_Text_Box_Soundifier", "Visit project source code"))

        instructions_layout.addWidget(instructions_scroll)
        instructions_layout.addLayout(links_buttons_layout)

        self.config_layout.addLayout(voice_layout)
        self.config_layout.addWidget(make_vertical_line())
        self.config_layout.addLayout(processing_layout)
        self.config_layout.addWidget(make_vertical_line())
        self.config_layout.addLayout(instructions_layout)

        self.nag_label = QLabel()
        self.nag_label.setOpenExternalLinks(True)
        self.nag_label.setTextFormat(Qt.TextFormat.MarkdownText)

        footer_layout = QHBoxLayout()

        signature = QLabel("<strong>Tool made by<br>floralQuaFloral</strong>")
        signature.setAlignment(Qt.AlignmentFlag.AlignBottom)
        signature.setFont(QFont("Arial", 11))

        self.preview_button = make_big_button("Preview Sound")
        self.preview_button.setCheckable(True)
        self.preview_button.clicked.connect(self.preview)

        self.save_button = make_big_button("Save Sound")
        self.save_button.clicked.connect(self.save)

        self.save_gif_button = make_big_button("Save Sound + Gif")
        self.save_gif_button.clicked.connect(self.save_with_gif)
        self.save_gif_button.setDisabled(True)

        footer_layout.addWidget(signature)
        footer_layout.addStretch()
        footer_layout.addWidget(self.preview_button)
        footer_layout.addWidget(make_vertical_line())
        footer_layout.addWidget(self.save_button)
        footer_layout.addWidget(make_vertical_line())
        footer_layout.addWidget(self.save_gif_button)
        # footer_layout.addStretch()

        layout = QVBoxLayout()
        layout.addWidget(self.text_box_display)
        layout.addLayout(self.config_layout)
        layout.addWidget(make_line(QFrame.Shape.HLine))
        layout.addWidget(self.nag_label)
        layout.addLayout(footer_layout)
        self.setLayout(layout)

        self.character_dropdown.setCurrentText("Default")
        self.change_character()

        self.recheck_eligibility()
        self.recheck_gif_eligibility()

        # show the window
        self.show()

    def set_text_box(self, gif_path, update_gif_path=True):
        if update_gif_path:
            self.gif_path = gif_path
        self.movie = QMovie(gif_path)
        self.movie.updated.connect(self.movie_signal)
        as_pixmap = QPixmap(gif_path)
        self.movie.setSpeed(round(self.settings.speed * 100))

        movie_aspect_ratio = as_pixmap.width() / as_pixmap.height()

        movie_final_height = 200
        movie_final_width = round(movie_final_height * movie_aspect_ratio)

        self.movie.setScaledSize(QSize(movie_final_width, movie_final_height))
        self.text_box_display.setMovie(self.movie)
        # self.setFixedSize(movie_final_width + 20, 670)
        self.movie.start()

    def movie_signal(self):
        if self.previewing and self.movie.currentFrameNumber() == 0:
            self.sound.play()

    def load_characters(self, is_initial=False):
        populate_characters_dictionary(get_voices_directory())

        self.universe_checkboxes = {}
        universes_layout = QVBoxLayout()

        universes = []
        for name in CHARACTERS:
            universe = CHARACTERS[name].universe
            if universe not in universes:
                universes.append(universe)

        is_first = True

        for universe in universes:
            universe_layout = QHBoxLayout()

            universe_label = QLabel(universe)

            self.universe_checkboxes[universe] = QCheckBox()

            self.universe_checkboxes[universe].setChecked(universe in DEFAULT_UNIVERSES)

            self.universe_checkboxes[universe].clicked.connect(self.update_dropdown)

            universe_layout.addWidget(universe_label)
            universe_layout.addWidget(self.universe_checkboxes[universe])

            if is_first:
                is_first = False
            else:
                universes_layout.addWidget(make_line(QFrame.Shape.HLine))
            universes_layout.addLayout(universe_layout)

        universes_layout.addStretch()

        self.universe_scroll_area.setLayout(universes_layout)
        self.update_dropdown()

    def is_character_enabled(self, character: BasicCharacter):
        return self.universe_checkboxes[character.universe].isChecked()

    def update_dropdown(self):
        prev_selection = self.character_dropdown.currentText()

        self.character_dropdown.clear()
        self.character_dropdown.addItem("Custom")

        for universe in self.universe_checkboxes:
            if self.universe_checkboxes[universe].isChecked():
                add_characters_from_universe(self.character_dropdown, universe)

        self.character_dropdown.setCurrentText(prev_selection)

        # add_characters_from_universe(self.character_dropdown, "Basic")
        # add_characters_from_universe(self.character_dropdown, "Undertale")
        # add_characters_from_universe(self.character_dropdown, "Deltarune")

    def recheck_eligibility(self):
        eligible = len(self.files) != 0
        self.save_button.setDisabled(not eligible)
        self.preview_button.setDisabled(not eligible)
        return eligible

    def recheck_gif_eligibility(self):
        eligible = self.recheck_eligibility() and self.settings.speed != 1
        self.save_gif_button.setDisabled(not eligible)
        return eligible

    def configure_universes(self, checked):
        self.add_file_button.setHidden(checked)
        self.remove_file_button.setHidden(checked)
        self.file_list.setHidden(checked)

        self.universe_scroll_area.setHidden(not checked)
        #
        # for label in self.universe_labels:
        #     label.setHidden(not checked)
        # for universe in self.universe_checkboxes:
        #     self.universe_checkboxes[universe].setHidden(not checked)

    def change_character(self):
        selected_character = self.character_dropdown.currentText()

        is_custom = selected_character == "Custom"
        self.file_list.setDisabled(not is_custom)
        self.add_file_button.setDisabled(not is_custom)
        self.remove_file_button.setDisabled(True)
        self.files.clear()
        if not is_custom:
            character: BasicCharacter = CHARACTERS[selected_character]
            self.files = character.voice_paths.copy()

            self.variant_label.setText(character.get_variant_name() + ": ")
            self.variant_checkbox.setChecked(False)
            has_variant = character.get_variant() != character
            self.variant_label.setDisabled(not has_variant)
            self.variant_label.setHidden(not has_variant)
            self.variant_checkbox.setDisabled(not has_variant)
            self.variant_checkbox.setHidden(not has_variant)

        self.update_file_list_widget()
        self.recheck_eligibility()
        self.end_preview()
        # self.preview(self.previewing)
        # self.play_voice_sound()

    def update_file_list_widget(self):
        self.file_list.clear()
        self.file_list.addItems(self.files)

    def toggle_variant(self):
        self.files = CHARACTERS[self.character_dropdown.currentText()].maybe_get_variant(self.variant_checkbox.isChecked()).voice_paths.copy()
        self.update_file_list_widget()

        self.recheck_eligibility()
        self.end_preview()
        # self.preview(self.previewing)
        # self.play_voice_sound()

    def select_file_from_list(self):
        self.remove_file_button.setDisabled(len(self.file_list.selectedItems()) == 0)

    def add_file(self):
        new_files = QFileDialog.getOpenFileNames(self, caption="Open File", filter="Wav audio files (*.wav)")[0]
        for new_file in new_files:
            if os.path.isfile(new_file) and new_file.endswith(".wav"):
                self.files.append(new_file)

        self.update_file_list_widget()
        self.recheck_eligibility()

    def remove_file(self):
        for remove_path in self.file_list.selectedItems():
            self.files.remove(remove_path.text())
        self.update_file_list_widget()
        self.remove_file_button.setDisabled(True)
        self.recheck_eligibility()

    def preview(self, checked):
        self.previewing = checked
        if checked:
            self.settings.output_audio_path = get_preview_path()
            self.settings.output_gif_path = None
            processor.make_and_save_blip_track(self.gif_path, self.settings, *self.files)
            self.sound = QSoundEffect()
            self.sound.setSource(QUrl.fromLocalFile(self.settings.output_audio_path))
            self.preview_button.setText("End Preview")
            self.movie.jumpToFrame(0)
        else:
            self.end_preview()
        self.nag()

    def end_preview(self):
        self.previewing = False
        if self.preview_button.isChecked():
            self.preview_button.setChecked(False)
        self.preview_button.setText("Preview Sound")
        self.sound.stop()

    def save(self):
        if self.recheck_eligibility():
            self.end_preview()
            self.settings.output_gif_path = None
            self.settings.output_audio_path = QFileDialog.getSaveFileName(self, caption="Save Soundifier Output", filter="Wav audio files (*.wav)")[0]
            if self.settings.output_audio_path != "":
                processor.make_and_save_blip_track(self.gif_path, self.settings, *self.files)
                self.nag()
                return True
        return False

    def save_with_gif(self):
        if self.save():
            self.settings.output_gif_path = QFileDialog.getSaveFileName(self, caption="Save Speed-Altered Gif", filter="Gif images (*.gif)")[0]
            processor.get_blip_timings_from_gif(self.gif_path, self.settings) # This is kinda dumb but whatever
            self.settings.output_gif_path = None
        self.nag()

    def nag(self):
        self.nag_label.setText("*Thanks for using the Soundifier! If this tool has been helpful for you and you'd like to say thanks, please consider [__leaving a tip on my Ko-fi__](https://ko-fi.com/floralquafloral).*")

    def play_voice_sound(self):
        self.sound.setSource(QUrl.fromLocalFile(random.choice(self.files)))
        self.sound.play()

def make_config_section(name):
    layout = QVBoxLayout()
    label = QLabel(f"{name}:")
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
    label.setFont(QFont("Arial", 16))
    layout.addWidget(label)
    return layout

def make_line(shape):
    frame = QFrame()
    frame.setFrameShape(shape)
    frame.setFrameShadow(QFrame.Shadow.Raised)
    return frame

def make_vertical_line():
    return make_line(QFrame.Shape.VLine)

def make_big_button(name):
    button = QPushButton(name)
    button.setFont(QFont("Arial", 22))
    return button

def get_voices_directory():
    return "./assets/builtin_voices/"

def get_preview_path():
    return "./assets/preview_output.wav"

def clean_name(name):
    name = name.replace(".wav", "")
    for i in range(10):
        name = name.replace(str(i), "")
    return name

def populate_characters_dictionary(path, prefix="", universe="Basic"):
    for character in os.listdir(path):
        full_path = path + character
        print(f"Checking out {full_path}")
        if os.path.isfile(full_path) and full_path.endswith(".wav"):
            CHARACTERS[prefix + character.replace(".wav", "")] = BasicCharacter([full_path], universe)
        elif os.path.isdir(full_path):
            if os.path.isfile(full_path + "/.multi"):
                print(f"Multiple characters in {character}, traversing...")
                populate_characters_dictionary(full_path + "/", prefix=prefix + character + "/", universe=character)
            else:
                if os.path.isfile(full_path + "/.variant"):
                    print(f"Character \"{character}\" has a variant!")
                    voice_paths = []
                    variant_paths = []
                    variant_name = "Variant"

                    for voice in os.listdir(full_path):
                        if voice.endswith(".wav"):
                            voice_clean_name = clean_name(voice)
                            if voice_clean_name.lower() == character.lower() or voice_clean_name == "":
                                voice_paths.append(full_path + "/" + voice)
                            else:
                                variant_name = voice_clean_name
                                variant_paths.append(full_path + "/" + voice)

                    if len(voice_paths) == 0:
                        print(f"Character supposedly has a variant but no non-variant sounds: {character}")
                        CHARACTERS[prefix + character] = BasicCharacter(variant_name, universe)
                    else:
                        CHARACTERS[prefix + character] = CharacterWithVariant(voice_paths, universe, variant_name, variant_paths)
                else:
                    voice_paths = []
                    for voice in os.listdir(full_path):
                        if voice.endswith(".wav"):
                            voice_paths.append(full_path + "/" + voice)
                    CHARACTERS[prefix + character] = BasicCharacter(voice_paths, universe)
        else:
            print(f"Something went wrong! Nothing at {full_path}!")

def add_characters_from_universe(dropdown, universe):
    for name in CHARACTERS:
        if CHARACTERS[name].universe == universe:
            dropdown.addItem(name)

def make_link_button(icon, url, tooltip):
    button = QPushButton()
    button.setIcon(QIcon(f"./assets/{icon}"))
    button.setIconSize(QSize(32, 32))
    button.setToolTip(tooltip)
    return button

if __name__ == '__main__':
    # create the QApplication
    app = QApplication(sys.argv)

    # create the main window
    window = MainWindow()

    # start the event loop
    sys.exit(app.exec())