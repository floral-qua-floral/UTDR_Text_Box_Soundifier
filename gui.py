import os
import random
import sys
from typing import List, Dict

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QMovie, QPixmap, QFont, QIcon, QDesktopServices, QDoubleValidator, QIntValidator
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QFrame, \
    QSizePolicy, QComboBox, QCheckBox, QAbstractItemView, QFileDialog, QScrollArea, QSlider, QLineEdit, QPlainTextEdit

import processor
import settings
from settings import SoundifierSettings

CHARACTERS = {}
DEFAULT_UNIVERSES = ["Basic", "Undertale", "Deltarune"]

class VoiceSettings:
    def __init__(self, interval, min_pitch, max_pitch, pitch_chance):
        self.interval = round(interval)
        self.min_pitch = min_pitch
        self.max_pitch = max_pitch
        self.pitch_chance = pitch_chance

class BasicCharacter:
    def __init__(self, voice_paths, universe, default_settings):
        self.voice_paths = voice_paths
        self.universe = universe
        self.default_settings = default_settings

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
    def __init__(self, voice_paths, universe, default_settings, variant_name, variant_voice_paths, variant_settings):
        super().__init__(voice_paths, universe, default_settings)
        self.variant_name = variant_name
        self.variant = BasicCharacter(variant_voice_paths, universe, variant_settings)


    def get_variant_name(self):
        return self.variant_name

    def get_variant(self):
        return self.variant

class TextBoxDisplayAndImporter(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window: MainWindow = parent
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):

        if event.mimeData().hasUrls:
            for url in event.mimeData().urls():
                if not url.path().endswith(".gif"):
                    event.ignore()
                    return

            event.acceptProposedAction()
            return

        event.ignore()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            paths.append(url.toLocalFile())
        print(f"Dropped in {paths}")
        self.main_window.set_gif_paths(paths)

    def mouseDoubleClickEvent(self, event):
        gifs = self.main_window.select_gifs_with_dialog()
        if len(gifs) > 0:
            self.main_window.set_gif_paths(gifs)

class MainWindow(QWidget):
    settings: SoundifierSettings

    gif_paths: List[str]
    preview_index: int
    movie: QMovie

    preview_index_display: QLabel

    text_box_display: QLabel

    remove_batch_file_button: QPushButton
    batch_file_list: QListWidget

    batch_mode_only_widgets: List[QWidget]

    character_dropdown: QComboBox
    universe_scroll_area: QScrollArea
    universe_checkboxes: Dict[str, QCheckBox]

    variant_label: QLabel
    variant_checkbox: QCheckBox

    universe_incompatible_widgets: List[QWidget]

    add_voice_file_button: QPushButton
    remove_voice_file_button: QPushButton

    voice_files: List[str]
    voice_file_list: QListWidget

    interval_slider: QSlider
    interval_display: QLineEdit
    mettatonize_widgets: List[QWidget]

    min_pitch_field: QLineEdit
    max_pitch_field: QLineEdit
    pitch_chance_field: QLineEdit

    speed_slider: QSlider
    speed_field: QLineEdit

    extra_noise_details: List[QWidget]

    overlap_prevention_details: List[QWidget]

    punctuation_skip_label: QLabel
    punctuation_skip_checkbox: QCheckBox

    punctuation_skip_incompatibility_label: QLabel

    punctuation_skip_details: List[QWidget]

    full_transcript: QPlainTextEdit

    nag_label: QLabel

    preview_button: QPushButton
    save_button: QPushButton
    save_gif_button: QPushButton

    sound: QSoundEffect
    previewing: bool
    previewing_altered_gif: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.settings = SoundifierSettings(get_preview_path())

        self.sound = QSoundEffect()
        self.sound.setVolume(1.0)
        self.previewing = False
        self.previewing_altered_gif = False
        self.gif_paths = []

        # set the window title
        self.setWindowTitle("UTDR Text Box Soundifier")

        text_box_layout = QHBoxLayout()

        preview_changer_layout = QVBoxLayout()

        previous_preview_button: QPushButton = QPushButton("Previous")
        previous_preview_button.setFixedHeight(40)
        previous_preview_button.clicked.connect(lambda: self.change_preview_index(-1))
        self.preview_index_display = QLabel("??/??")
        self.preview_index_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_index_display.setFont(QFont("Arial", 16))
        next_preview_button: QPushButton = QPushButton("Next")
        next_preview_button.setFixedHeight(40)
        next_preview_button.clicked.connect(lambda: self.change_preview_index(1))

        preview_changer_layout.addStretch()
        preview_changer_layout.addWidget(previous_preview_button)
        preview_changer_layout.addWidget(self.preview_index_display)
        preview_changer_layout.addWidget(next_preview_button)
        preview_changer_layout.addStretch()

        self.text_box_display = TextBoxDisplayAndImporter(self)
        self.text_box_display.setScaledContents(False)

        text_box_layout.addStretch()
        text_box_layout.addLayout(preview_changer_layout)
        text_box_layout.addWidget(self.text_box_display)
        text_box_layout.addStretch()

        config_layout = QHBoxLayout()

        batch_mode_layout, batch_mode_label = make_config_section("Batch Mode")

        batch_file_manage_layout = QHBoxLayout()

        add_batch_file_button: QPushButton = QPushButton("Add File")
        add_batch_file_button.clicked.connect(self.add_batch_file)
        self.remove_batch_file_button: QPushButton = QPushButton("Remove File")
        self.remove_batch_file_button.setDisabled(True)
        self.remove_batch_file_button.clicked.connect(self.remove_batch_file)

        batch_file_manage_layout.addWidget(add_batch_file_button)
        batch_file_manage_layout.addWidget(self.remove_batch_file_button)

        self.batch_file_list = QListWidget()
        self.batch_file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.batch_file_list.itemSelectionChanged.connect(self.select_batch_file_from_list)

        batch_mode_explanation = QLabel("<em>All exports in Batch Mode will use the same voice and settings for every text box!</em>")
        batch_mode_explanation.setWordWrap(True)

        batch_mode_layout.addLayout(batch_file_manage_layout)
        batch_mode_layout.addWidget(self.batch_file_list)
        batch_mode_layout.addWidget(batch_mode_explanation)

        voice_layout = make_config_section("Voice")[0]

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

        manage_voice_files_layout = QHBoxLayout()

        self.add_voice_file_button = QPushButton("Add File")
        self.add_voice_file_button.clicked.connect(self.add_voice_sfx)
        self.remove_voice_file_button = QPushButton("Remove File")
        self.remove_voice_file_button.setDisabled(True)
        self.remove_voice_file_button.clicked.connect(self.remove_voice_sfx)

        manage_voice_files_layout.addWidget(self.add_voice_file_button)
        manage_voice_files_layout.addWidget(self.remove_voice_file_button)

        self.voice_files = []
        self.voice_file_list = QListWidget()
        self.voice_file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.voice_file_list.itemSelectionChanged.connect(self.select_voice_file_from_list)

        interval_layout = QHBoxLayout()

        interval_label = QLabel("Interval:")

        self.interval_slider: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.interval_slider.setRange(1, 10)
        self.interval_slider.valueChanged.connect(self.change_interval)

        self.interval_display = QLineEdit("??")
        self.interval_display.setFixedWidth(20)

        mettatonize_label = QLabel("Mettatonize:")
        mettatonize_checkbox: QCheckBox = QCheckBox()
        mettatonize_checkbox.clicked.connect(self.toggle_mettatonize)

        self.mettatonize_widgets = [
            mettatonize_label,
            mettatonize_checkbox
        ]

        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_slider)
        interval_layout.addWidget(self.interval_display)
        interval_layout.addWidget(mettatonize_label)
        interval_layout.addWidget(mettatonize_checkbox)

        pitch_layout = QHBoxLayout()

        pitch_label = QLabel("Pitch range:")

        self.min_pitch_field = make_pitch_field(self.change_min_pitch)

        pitch_mid_label = QLabel("to")

        self.max_pitch_field = make_pitch_field(self.change_max_pitch)

        pitch_chance_label = QLabel("Chance: ")

        self.pitch_chance_field = make_pitch_field(self.change_pitch_chance)

        pitch_layout.addWidget(pitch_label)
        pitch_layout.addWidget(self.min_pitch_field)
        pitch_layout.addWidget(pitch_mid_label)
        pitch_layout.addWidget(self.max_pitch_field)
        pitch_layout.addStretch()
        pitch_layout.addWidget(pitch_chance_label)
        pitch_layout.addWidget(self.pitch_chance_field)

        voice_layout.addLayout(character_layout)
        voice_layout.addLayout(variant_layout)
        voice_layout.addWidget(self.universe_scroll_area)
        voice_layout.addLayout(manage_voice_files_layout)
        voice_layout.addWidget(self.voice_file_list)
        voice_layout.addLayout(interval_layout)
        voice_layout.addLayout(pitch_layout)

        processing_layout = make_config_section("Processing")[0]

        speed_layout = QHBoxLayout()

        speed_label = QLabel("Speed:")

        self.speed_slider: QSlider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 100)
        self.speed_slider.setValue(100)
        self.speed_slider.sliderMoved.connect(self.speed_slider_moved)

        self.speed_field: QLineEdit = QLineEdit("1.00")
        self.speed_field.setFixedWidth(30)
        self.speed_field.textChanged.connect(self.speed_field_written)

        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_field)

        easy_align_layout = QHBoxLayout()
        easy_align_label = QLabel("Easy Alignment:")
        easy_align_checkbox: QCheckBox = QCheckBox()
        easy_align_checkbox.setChecked(True)

        skip_first_blip_label = QLabel("Skip First Noise:")
        skip_first_blip_checkbox: QCheckBox = QCheckBox()

        easy_align_layout.addWidget(easy_align_label)
        easy_align_layout.addWidget(easy_align_checkbox)
        easy_align_layout.addWidget(make_vertical_line())
        easy_align_layout.addWidget(skip_first_blip_label)
        easy_align_layout.addWidget(skip_first_blip_checkbox)

        extra_noise_layout = QHBoxLayout()

        extra_noise_label = QLabel("Insert Extra Noise:")
        extra_noise_checkbox: QCheckBox = QCheckBox()
        extra_noise_checkbox.clicked.connect(self.toggle_extra_noise)

        extra_noise_at_label = QLabel("@")

        extra_noise_moment_field = make_ms_field(1000, self.change_extra_noise_time)

        extra_noise_ms_label = QLabel(" ms")

        self.extra_noise_details = [
            extra_noise_at_label,
            extra_noise_moment_field,
            extra_noise_ms_label
        ]

        extra_noise_layout.addWidget(extra_noise_label)
        extra_noise_layout.addWidget(extra_noise_checkbox)
        extra_noise_layout.addWidget(extra_noise_at_label)
        extra_noise_layout.addWidget(extra_noise_moment_field)
        extra_noise_layout.addWidget(extra_noise_ms_label)

        olp_toggle_layout = QHBoxLayout()

        overlap_prevention_label = QLabel("<strong>Overlap Prevention:</strong>")

        overlap_prevention_checkbox: QCheckBox = QCheckBox()
        overlap_prevention_checkbox.clicked.connect(self.toggle_olp)

        olp_toggle_layout.addStretch()
        olp_toggle_layout.addWidget(overlap_prevention_label)
        olp_toggle_layout.addWidget(overlap_prevention_checkbox)
        olp_toggle_layout.addStretch()

        olp_max_overlap_layout = QHBoxLayout()

        olp_max_overlap_label = QLabel("Maximum overlap:")

        olp_max_overlap_field = make_ms_field(20, self.change_max_overlap)

        olp_max_overlap_ms_label = QLabel("ms")

        olp_max_overlap_layout.addWidget(olp_max_overlap_label)
        olp_max_overlap_layout.addWidget(olp_max_overlap_field)
        olp_max_overlap_layout.addWidget(olp_max_overlap_ms_label)
        olp_max_overlap_layout.addStretch()

        olp_fade_duration_layout = QHBoxLayout()

        olp_fade_duration_label = QLabel("Fade Duration:")

        olp_fade_duration_field = make_ms_field(16, self.change_fade_duration)

        olp_fade_duration_ms_label = QLabel("ms")

        olp_fade_duration_layout.addWidget(olp_fade_duration_label)
        olp_fade_duration_layout.addWidget(olp_fade_duration_field)
        olp_fade_duration_layout.addWidget(olp_fade_duration_ms_label)
        olp_fade_duration_layout.addStretch()

        self.overlap_prevention_details = [
            olp_max_overlap_label,
            olp_max_overlap_field,
            olp_max_overlap_ms_label,
            olp_fade_duration_label,
            olp_fade_duration_field,
            olp_fade_duration_ms_label
        ]

        punctuation_skip_toggle_layout = QHBoxLayout()

        self.punctuation_skip_label = QLabel("<strong>Skip Punctuation:</strong>")

        self.punctuation_skip_checkbox: QCheckBox = QCheckBox()
        self.punctuation_skip_checkbox.clicked.connect(self.toggle_punctuation_skip)

        punctuation_skip_toggle_layout.addStretch()
        punctuation_skip_toggle_layout.addWidget(self.punctuation_skip_label)
        punctuation_skip_toggle_layout.addWidget(self.punctuation_skip_checkbox)
        punctuation_skip_toggle_layout.addStretch()

        self.punctuation_skip_incompatibility_label = QLabel(make_punctuation_skip_availability_excuse("IF YOU'RE SEEING THIS, THERE'S AN ERROR!"))
        self.punctuation_skip_incompatibility_label.setWordWrap(True)
        self.punctuation_skip_incompatibility_label.setFont(QFont("Arial", 12))
        self.punctuation_skip_incompatibility_label.setDisabled(True)

        skip_non_alphanumeric_layout = QHBoxLayout()

        skip_non_alphanumeric_label = QLabel("Skip all non-alphanumeric characters:")

        skip_non_alphanumeric_checkbox: QCheckBox = QCheckBox()
        skip_non_alphanumeric_checkbox.setChecked(True)
        skip_non_alphanumeric_checkbox.clicked.connect(self.toggle_skip_non_alphanumeric)

        skip_non_alphanumeric_layout.addWidget(skip_non_alphanumeric_label)
        skip_non_alphanumeric_layout.addWidget(skip_non_alphanumeric_checkbox)

        skip_characters_layout = QHBoxLayout()

        skip_characters_label = QLabel("Skip all of:")

        skip_characters_field: QLineEdit = QLineEdit(self.settings.skip_characters)
        skip_characters_field.textEdited.connect(self.edit_skip_characters)

        skip_characters_layout.addWidget(skip_characters_label)
        skip_characters_layout.addWidget(skip_characters_field)

        punctuation_skip_require_label = QLabel("In order to use Punctuation Skipping, the contents of the text box <u><strong>must</strong></u> be copied below:")
        punctuation_skip_require_label.setWordWrap(True)

        self.full_transcript = QPlainTextEdit()
        self.full_transcript.setFixedWidth(225)
        self.full_transcript.textChanged.connect(self.edit_transcript)

        self.punctuation_skip_details = [
            skip_non_alphanumeric_label,
            skip_non_alphanumeric_checkbox,
            skip_characters_label,
            skip_characters_field,
            punctuation_skip_require_label,
            self.full_transcript
        ]

        processing_layout.addLayout(speed_layout)
        processing_layout.addLayout(easy_align_layout)
        processing_layout.addLayout(extra_noise_layout)
        processing_layout.addWidget(make_horizontal_line())
        processing_layout.addLayout(olp_toggle_layout)
        processing_layout.addLayout(olp_max_overlap_layout)
        processing_layout.addLayout(olp_fade_duration_layout)
        processing_layout.addWidget(make_horizontal_line())
        processing_layout.addLayout(punctuation_skip_toggle_layout)
        processing_layout.addStretch()
        processing_layout.addWidget(self.punctuation_skip_incompatibility_label)
        processing_layout.addLayout(skip_non_alphanumeric_layout)
        processing_layout.addLayout(skip_characters_layout)
        processing_layout.addWidget(punctuation_skip_require_label)
        processing_layout.addWidget(self.full_transcript)
        processing_layout.addStretch(2)

        instructions_layout = make_config_section("Instructions")[0]
        instructions_steps_label = QLabel(
        """
        <p style="text-indent:10px;">1. Use <a href="https://www.demirramon.com/generators/undertale_text_box_generator">Demirramon's Undertale Text Box Generator</a> to create an animated text box. (Make sure "Export settings>Format" is set to "Animated GIF".)</p>
        <p style="text-indent:10px;">2. Import the animated text box into the Soundifier. (Tip: You can double-click the Soundifier's text box, or drag-and-drop the gif onto it instead. You can even drag it directly from the browser!)</p>
        <p style="text-indent:10px;">3. Configure the Soundifier's voice and processing settings to your liking.</p>
        <p style="text-indent:10px;">4. Press "Preview Sound" to hear the output in sync with the preview at the top, or press "Save Sound" when you're done. If you've adjusted any setting that would modify the gif, you can save that too with "Save Sound + Gif".</p>
        <p style="text-indent:10px;">5. Put the exported sound into the video editing software of your choice, at the same position of the timeline as the text box gif.</p>
        <p>Tip: For slowed-down text boxes, you'll get better results putting the <em>original</em> text box straight from Demirramon's generator into your video editor and slowing it down using the editor controls, instead of using the "Save Sound + Gif" feature.</p>
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

        links_buttons_layout.addWidget(make_link_button("generator.png", "https://www.demirramon.com/generators/undertale_text_box_generator", "Demirramon's Undertale Text Box Generator"))
        links_buttons_layout.addStretch()
        links_buttons_layout.addWidget(make_vertical_line())
        links_buttons_layout.addStretch()
        links_buttons_layout.addWidget(make_link_button("ko-fi.png", "https://ko-fi.com/floralquafloral", "Button for coolest people"))
        links_buttons_layout.addWidget(make_link_button("github.png", "https://github.com/floral-qua-floral/UTDR_Text_Box_Soundifier", "Visit project source code"))

        instructions_layout.addWidget(instructions_scroll)
        instructions_layout.addLayout(links_buttons_layout)

        batch_mode_divider = make_vertical_line()

        config_layout.addLayout(batch_mode_layout)
        config_layout.addWidget(batch_mode_divider)
        config_layout.addLayout(voice_layout)
        config_layout.addWidget(make_vertical_line())
        config_layout.addLayout(processing_layout)
        config_layout.addWidget(make_vertical_line())
        config_layout.addLayout(instructions_layout)

        self.nag_label = QLabel()
        self.nag_label.setOpenExternalLinks(True)
        self.nag_label.setTextFormat(Qt.TextFormat.MarkdownText)

        footer_layout = QHBoxLayout()

        signature = QLabel("<strong>Tool made by<br>floralQuaFloral</strong>")
        signature.setAlignment(Qt.AlignmentFlag.AlignBottom)
        signature.setFont(QFont("Arial", 11))

        self.preview_button = make_big_button("Preview")
        self.preview_button.setCheckable(True)
        self.preview_button.clicked.connect(self.toggle_preview)

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
        layout.addLayout(text_box_layout)
        layout.addWidget(make_horizontal_line())
        layout.addLayout(config_layout)
        layout.addWidget(make_horizontal_line())
        layout.addWidget(self.nag_label)
        layout.addLayout(footer_layout)
        self.setLayout(layout)

        self.universe_incompatible_widgets = [
            self.add_voice_file_button,
            self.remove_voice_file_button,
            self.voice_file_list,

            interval_label,
            self.interval_slider,
            self.interval_display,
            mettatonize_label,
            mettatonize_checkbox,

            pitch_label,
            self.min_pitch_field,
            pitch_mid_label,
            self.max_pitch_field,
            pitch_chance_label,
            self.pitch_chance_field
        ]

        self.batch_mode_only_widgets = [
            previous_preview_button,
            self.preview_index_display,
            next_preview_button,

            batch_mode_label,
            batch_mode_divider,

            add_batch_file_button,
            self.remove_batch_file_button,
            self.batch_file_list,
            batch_mode_explanation
        ]

        self.set_gif_paths(["./assets/hint_text_box.gif", "./test input/flowey.gif"])

        self.character_dropdown.setCurrentText("Default")
        self.change_character()

        self.change_interval(1)

        self.toggle_extra_noise(False)

        self.toggle_olp(False)

        self.toggle_punctuation_skip(False)

        self.recheck_eligibility()
        self.recheck_gif_eligibility()

        # show the window
        self.show()

    def set_gif_paths(self, new_gif_paths, reset_preview_index=True):
        self.gif_paths = new_gif_paths.copy()
        self.update_batch_file_list_widget()
        self.previewing_altered_gif = False
        self.toggle_batch_mode(len(self.gif_paths) > 1)

        if reset_preview_index:
            self.preview_index = 0
        self.change_preview_index(0)
        self.recheck_punctuation_skip_availability()

    def change_preview_index(self, offset):
        self.preview_index = (self.preview_index + offset) % len(self.gif_paths)
        self.set_movie(self.gif_paths[self.preview_index])
        self.preview_index_display.setText(f"{self.preview_index + 1}/{len(self.gif_paths)}")
        self.end_preview()

    def set_movie(self, movie_path):
        print(f"Setting movie to {movie_path}")
        self.movie: QMovie = QMovie(movie_path)
        self.movie.updated.connect(self.movie_signal)
        as_pixmap = QPixmap(movie_path)
        # self.movie.setSpeed(round(self.settings.speed * 100))

        movie_aspect_ratio = as_pixmap.width() / as_pixmap.height()

        movie_final_width = 746
        movie_final_height = round(movie_final_width / movie_aspect_ratio)
        self.setFixedHeight(490 + movie_final_height)

        self.movie.setScaledSize(QSize(movie_final_width, movie_final_height))
        self.text_box_display.setMovie(self.movie)
        # self.setFixedSize(movie_final_width + 20, 670)
        self.movie.start()

    def toggle_batch_mode(self, is_batch):
        fixed_width = 1040 if is_batch else 766
        self.setFixedWidth(fixed_width)

        for widget in self.batch_mode_only_widgets:
            widget.setHidden(not is_batch)

    def movie_signal(self):
        if self.previewing and self.movie.currentFrameNumber() == 0:
            self.sound.play()

    def add_batch_file(self):
        add_gifs = self.select_gifs_with_dialog()
        if len(add_gifs) != 0:
            new_gifs = self.gif_paths.copy()
            for add_gif in add_gifs:
                if add_gif not in new_gifs:
                    new_gifs.append(add_gif)

            if len(new_gifs) != len(self.gif_paths):
                self.set_gif_paths(new_gifs, reset_preview_index=False)

    def remove_batch_file(self):
        new_gif_paths = self.gif_paths.copy()
        for remove_path in self.batch_file_list.selectedItems():
            new_gif_paths.remove(remove_path.text())

        self.remove_batch_file_button.setDisabled(True)
        if len(new_gif_paths) == 0:
            new_gif_paths.append("./assets/hint_text_box.gif")

        self.set_gif_paths(new_gif_paths, reset_preview_index=False)

    def select_batch_file_from_list(self):
        selections_count = len(self.batch_file_list.selectedItems())
        self.remove_batch_file_button.setDisabled(selections_count == 0)
        if selections_count == 1:
            self.preview_index = self.batch_file_list.selectedIndexes()[0].row()
            self.change_preview_index(0)

    def update_batch_file_list_widget(self):
        self.batch_file_list.clear()
        self.batch_file_list.addItems(self.gif_paths)

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
                universes_layout.addWidget(make_horizontal_line())
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
        self.end_preview()
        eligible = len(self.voice_files) != 0 and not (self.settings.skip_punctuation and self.settings.full_text == "")
        self.save_button.setDisabled(not eligible)
        self.preview_button.setDisabled(not eligible)
        return eligible

    def recheck_gif_eligibility(self):
        eligible = self.recheck_eligibility() and (self.settings.speed != 1 or (self.settings.mettatonize and self.settings.interval != 1))
        self.save_gif_button.setDisabled(not eligible)
        return eligible

    def configure_universes(self, checked):
        for hideable_thing in self.universe_incompatible_widgets:
            hideable_thing.setHidden(checked)

        self.universe_scroll_area.setHidden(not checked)
        #
        # for label in self.universe_labels:
        #     label.setHidden(not checked)
        # for universe in self.universe_checkboxes:
        #     self.universe_checkboxes[universe].setHidden(not checked)

    def change_character(self):
        selected_character = self.character_dropdown.currentText()

        is_custom = selected_character == "Custom"
        self.voice_file_list.setDisabled(not is_custom)
        self.add_voice_file_button.setDisabled(not is_custom)
        self.remove_voice_file_button.setDisabled(True)
        self.voice_files.clear()
        if is_custom:
            self.apply_voice_settings(VoiceSettings(1, 1, 1, 1))
        else:
            character: BasicCharacter = CHARACTERS[selected_character]
            self.voice_files = character.voice_paths.copy()

            self.variant_label.setText(character.get_variant_name() + ": ")
            self.variant_checkbox.setChecked(False)
            has_variant = character.get_variant() != character
            self.variant_label.setDisabled(not has_variant)
            self.variant_label.setHidden(not has_variant)
            self.variant_checkbox.setDisabled(not has_variant)
            self.variant_checkbox.setHidden(not has_variant)

            self.apply_voice_settings(character.default_settings)

            # This is hardcoded because it's literally just the one guy
            is_mettaton = selected_character == "Undertale/Mettaton" or selected_character == "Mettaton"
            self.settings.mettatonize = is_mettaton
            self.mettatonize_widgets[1].setChecked(is_mettaton)

            # self.change_interval(character.default_settings.interval, from_slider=False)

        self.update_voice_file_list_widget()
        self.recheck_eligibility()
        self.end_preview()

    def apply_voice_settings(self, default_settings: VoiceSettings):
        self.interval_slider.setValue(default_settings.interval)
        self.min_pitch_field.setText(str(default_settings.min_pitch))
        self.max_pitch_field.setText(str(default_settings.max_pitch))
        self.pitch_chance_field.setText(str(default_settings.pitch_chance))

    def update_voice_file_list_widget(self):
        self.voice_file_list.clear()
        self.voice_file_list.addItems(self.voice_files)

    def toggle_variant(self):
        new_character = CHARACTERS[self.character_dropdown.currentText()].maybe_get_variant(self.variant_checkbox.isChecked())
        self.voice_files = new_character.voice_paths.copy()
        self.update_voice_file_list_widget()

        print(new_character.voice_paths)
        print(new_character.default_settings.interval)
        self.apply_voice_settings(new_character.default_settings)

        self.recheck_eligibility()
        self.end_preview()
        # self.preview(self.previewing)
        # self.play_voice_sound()

    def select_voice_file_from_list(self):
        self.remove_voice_file_button.setDisabled(len(self.voice_file_list.selectedItems()) == 0)

    def add_voice_sfx(self):
        new_files = QFileDialog.getOpenFileNames(self, caption="Open File", filter="Wav audio files (*.wav)")[0]
        for new_file in new_files:
            if os.path.isfile(new_file) and new_file.endswith(".wav"):
                self.voice_files.append(new_file)

        self.update_voice_file_list_widget()
        self.recheck_eligibility()

    def remove_voice_sfx(self):
        for remove_path in self.voice_file_list.selectedItems():
            self.voice_files.remove(remove_path.text())
        self.update_voice_file_list_widget()
        self.remove_voice_file_button.setDisabled(True)
        self.recheck_eligibility()

    def change_interval(self, interval):
        self.settings.interval = interval
        self.interval_display.setText(str(interval))

        for widget in self.mettatonize_widgets:
            widget.setDisabled(interval == 1)

        self.recheck_punctuation_skip_availability()

        self.recheck_gif_eligibility()

    def toggle_mettatonize(self, mettatonize):
        self.settings.mettatonize = mettatonize
        self.recheck_gif_eligibility()

    def recheck_punctuation_skip_availability(self):
        # available = self.settings.interval == 1 and len(self.gif_paths) == 1

        available = True
        excuse = "IF YOU'RE SEEING THIS, I'M BROKEN!! YIKES!"
        if self.settings.interval != 1:
            available = False
            excuse = make_punctuation_skip_availability_excuse("when interval isn't set to exactly 1.")
        if len(self.gif_paths) != 1:
            available = False
            excuse = make_punctuation_skip_availability_excuse(" in batch mode.")

        if not available:
            self.punctuation_skip_checkbox.setChecked(False)
            self.toggle_punctuation_skip(False)

        self.punctuation_skip_incompatibility_label.setText(excuse)
        self.punctuation_skip_incompatibility_label.setHidden(available)

        self.punctuation_skip_label.setDisabled(not available)
        self.punctuation_skip_checkbox.setDisabled(not available)

        for widget in self.punctuation_skip_details:
            widget.setHidden(not available)

    def change_min_pitch(self, new_min):
        try:
            self.settings.min_pitch = float(new_min)
            self.end_preview()
        except ValueError:
            pass

    def change_max_pitch(self, new_max):
        try:
            self.settings.max_pitch = float(new_max)
            self.end_preview()
        except ValueError:
            pass

    def change_pitch_chance(self, new_chance):
        try:
            self.settings.random_pitch_chance = float(new_chance)
            self.end_preview()
        except ValueError:
            pass

    def speed_slider_moved(self, new_speed):
        self.speed_field.setText(f"{(new_speed / 100):.2f}")

    def speed_field_written(self, new_speed):
        try:
            self.settings.speed = float(new_speed)
            self.speed_slider.setValue(round(self.settings.speed * 100))
            self.recheck_gif_eligibility()
        except ValueError:
            pass

    def toggle_easy_align(self, checked):
        self.settings.easy_align = checked

        self.end_preview()

    def toggle_extra_noise(self, checked):
        self.settings.do_extra_noise = checked

        for widget in self.extra_noise_details:
            widget.setDisabled(not checked)

        self.end_preview()

    def change_extra_noise_time(self, new_time):
        try:
            self.settings.extra_noise_time = int(new_time)
            self.end_preview()
        except ValueError:
            pass

    def toggle_olp(self, checked):
        self.settings.do_overlap_prevention = checked

        for widget in self.overlap_prevention_details:
            widget.setDisabled(not checked)

        self.end_preview()

    def change_max_overlap(self, new_max):
        try:
            self.settings.olp_hard_cutoff_leniency = int(new_max)
            self.end_preview()
        except ValueError:
            pass

    def change_fade_duration(self, new_duration):
        try:
            self.settings.olp_fade_duration = int(new_duration)
            self.end_preview()
        except ValueError:
            pass

    def toggle_punctuation_skip(self, checked):
        self.settings.skip_punctuation = checked

        for widget in self.punctuation_skip_details:
            widget.setDisabled(not checked)

        self.recheck_eligibility()

    def toggle_skip_non_alphanumeric(self, checked):
        self.settings.skip_non_alphanumeric = checked
        self.end_preview()

    def edit_skip_characters(self, new_string):
        self.settings.skip_characters = new_string
        self.end_preview()

    def edit_transcript(self):
        self.settings.full_text = self.full_transcript.toPlainText()
        self.recheck_eligibility()

    def toggle_preview(self, checked):
        self.previewing = checked
        if checked:
            self.settings.output_audio_path = get_preview_path()
            self.settings.output_gif_path = None
            processor.make_and_save_blip_track(self.gif_paths[self.preview_index], self.settings, *self.voice_files)
            self.sound = QSoundEffect()
            self.sound.setSource(QUrl.fromLocalFile(self.settings.output_audio_path))
            self.preview_button.setText("End Preview")

            if self.settings.speed != 1 or (self.settings.mettatonize and self.settings.interval != 1):
                self.settings.output_gif_path = "./assets/preview_output.gif"
                processor.get_blip_timings_from_gif(self.gif_paths[self.preview_index], self.settings)
                self.set_movie("./assets/preview_output.gif")
                # self.set_gif_paths(["./assets/preview_output.gif"], from_preview=True)
                self.previewing_altered_gif = True
            else:
                self.movie.jumpToFrame(0)
        else:
            self.end_preview()
        # self.nag()

    def end_preview(self):
        self.previewing = False
        if self.previewing_altered_gif:
            self.set_movie(self.gif_paths[self.preview_index])
        if self.preview_button.isChecked():
            self.preview_button.setChecked(False)
        self.preview_button.setText("Preview")
        self.sound.stop()

    def save(self):
        self.save_with_maybe_gif(False)

    def save_with_maybe_gif(self, do_gifs):
        if not self.recheck_eligibility():
            return False

        saved_any = False

        if len(self.gif_paths) == 1:
            audio_path = QFileDialog.getSaveFileName(self, caption="Save Soundifier Output", filter="Wav audio files (*.wav)")[0]

            self.settings.output_gif_path = None
            if do_gifs:
                self.settings.output_gif_path = QFileDialog.getSaveFileName(self,
                        caption="Save Speed-Altered Gif", filter="Gif images (*.gif)")[0]

            saved_any = self.save_blip_track(self.gif_paths[0], audio_path)

        else:
            output_folder = QFileDialog.getExistingDirectory(caption="Save Soundifier Output")

            self.settings.output_gif_path = None

            if output_folder != "":
                for save_for_gif in self.gif_paths:
                    output_base_name = output_folder + "/" + save_for_gif.split("/")[-1][:-4]
                    self.settings.output_gif_path = output_base_name + ".gif"
                    if self.save_blip_track(save_for_gif, output_base_name + ".wav"):
                        saved_any = True

        if saved_any:
            self.nag()
        return saved_any

    def save_with_gif(self):
        self.save_with_maybe_gif(True)

    def save_blip_track(self, for_gif_path, output_path):
        self.settings.output_audio_path = output_path
        if self.settings.output_gif_path is not None:
            self.settings.output_gif_path = output_path[:-4] + ".gif"
        if self.settings.output_audio_path != "":
            try:
                processor.make_and_save_blip_track(for_gif_path, self.settings, *self.voice_files)
                return True
            except Exception as e:
                print(f"Failed to save sound for gif {for_gif_path}.\n\tCaused by: {e}")
        return False

    def nag(self):
        self.nag_label.setText("*Thanks for using the Soundifier! If this tool has been helpful for you and you'd like to say thanks, please consider [__leaving a tip on my Ko-fi__](https://ko-fi.com/floralquafloral).*")

    def play_voice_sound(self):
        self.sound.setSource(QUrl.fromLocalFile(random.choice(self.voice_files)))
        self.sound.play()

    def select_gifs_with_dialog(self):
        return QFileDialog.getOpenFileNames(self, caption="Open File", filter="Gif images (*.gif)")[0]

def make_config_section(name):
    layout = QVBoxLayout()
    label = QLabel(f"{name}:")
    label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    label.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred))
    label.setFont(QFont("Arial", 16))
    layout.addWidget(label)
    return layout, label

def make_line(shape):
    frame = QFrame()
    frame.setFrameShape(shape)
    frame.setFrameShadow(QFrame.Shadow.Raised)
    return frame

def make_vertical_line():
    return make_line(QFrame.Shape.VLine)

def make_horizontal_line():
    return make_line(QFrame.Shape.HLine)

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

def get_default_settings(full_path):
    if full_path.endswith(".wav"):
        full_path = full_path[:-4]
    else:
        full_path += "/"
    full_path += ".default_settings"

    fallback = VoiceSettings(1, 1, 1, 1)

    if os.path.isfile(full_path):
        with open(full_path, "r") as file:
            fallback = get_settings_from_file(file, fallback)

    return fallback

def get_settings_from_file(file, fallback):
    first_line = file.readline()
    if first_line == "":
        return fallback
    return VoiceSettings(
        number_from_line(first_line),
        number_from_line(file.readline()),
        number_from_line(file.readline()),
        number_from_line(file.readline())
    )

def number_from_line(line):
    if line == "":
        return 1
    if line.isdigit():
        return int(line)
    return float(line)

def populate_characters_dictionary(path, prefix="", universe="Basic"):
    for character in os.listdir(path):
        full_path = path + character
        print(f"Checking out {full_path}")
        if os.path.isfile(full_path) and full_path.endswith(".wav"):
            CHARACTERS[prefix + character.replace(".wav", "")] = BasicCharacter([full_path], universe, get_default_settings(full_path))
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
                        CHARACTERS[prefix + character] = BasicCharacter(variant_name, universe, get_default_settings(full_path))
                    else:
                        default_settings = get_default_settings(full_path)
                        with open(full_path + "/.variant", "r") as file:
                            variant_settings = get_settings_from_file(file, default_settings)
                        CHARACTERS[prefix + character] = CharacterWithVariant(voice_paths, universe, default_settings, variant_name, variant_paths, variant_settings)
                else:
                    voice_paths = []
                    for voice in os.listdir(full_path):
                        if voice.endswith(".wav"):
                            voice_paths.append(full_path + "/" + voice)
                    CHARACTERS[prefix + character] = BasicCharacter(voice_paths, universe, get_default_settings(full_path))
        else:
            print(f"Something went wrong! Nothing at {full_path}!")

def add_characters_from_universe(dropdown, universe):
    for name in CHARACTERS:
        if CHARACTERS[name].universe == universe:
            dropdown.addItem(name)

def make_link_button(icon, url, tooltip):
    button: QPushButton = QPushButton()
    button.setIcon(QIcon(f"./assets/{icon}"))
    button.setIconSize(QSize(32, 32))
    button.setToolTip(tooltip)
    button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
    return button

def make_pitch_field(connection):
    text_field: QLineEdit = QLineEdit("1.00")
    text_field.setValidator(QDoubleValidator())
    text_field.setFixedWidth(34)
    text_field.textChanged.connect(connection)
    return text_field

def make_ms_field(default, connection):
    text_field: QLineEdit = QLineEdit(str(default))
    text_field.setValidator(QIntValidator())
    text_field.setFixedWidth(40)
    text_field.textChanged.connect(connection)
    return text_field

def make_punctuation_skip_availability_excuse(excuse):
    return f"<br><em>Sorry, Punctuation Skipping does not work {excuse} <strong>;-;</strong></em>"

if __name__ == '__main__':
    # create the QApplication
    app = QApplication(sys.argv)

    # create the main window
    window = MainWindow()

    # start the event loop
    sys.exit(app.exec())