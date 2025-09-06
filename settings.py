from typing import Optional

class SoundifierSettings:
    def __init__(self, output_audio_path: str):
        self.output_audio_path: str = output_audio_path
        self.output_gif_path: Optional[str] = None

        self.speed: float = 1

        self.do_overlap_prevention: bool = False
        self.olp_hard_cutoff_leniency: int = 20
        self.olp_fade_duration: int = 16

        self.interval: int = 1
        self.mettatonize: bool = False

        self.random_pitch_chance: float = 1
        self.min_pitch: float = 1
        self.max_pitch: float = 1

        self.easy_align: bool = True
        self.skip_first_blip: bool = False
        self.cutoff_distance: int = 1500

        self.do_extra_noise: bool = False
        self.extra_noise_moment: int = 0

        self.skip_punctuation: bool = True
        self.skip_non_alphanumeric = True
        self.skip_characters: str = ""
        self.full_text: str = ""
