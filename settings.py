from typing import Optional

class SoundifierSettings:
    output_audio_path: str
    output_gif_path: Optional[str]

    do_overlap_prevention: bool
    olp_hard_cutoff_leniency: int
    olp_fade_duration: int
    speed: float
    interval: int

    mettatonize: bool

    def __init__(self,
                output_audio_path: str,
                output_gif_path: str = None,

                speed: float = 1,

                overlap_hard_cutoff_leniency: int = 20,
                overlap_fade_duration: int = 16,

                interval: int = 3,
                mettatonize_gif: bool = True
        ):
        self.output_audio_path = output_audio_path
        self.output_gif_path = output_gif_path

        self.speed = speed

        self.do_overlap_prevention = overlap_hard_cutoff_leniency != 0
        self.olp_hard_cutoff_leniency = overlap_hard_cutoff_leniency
        self.olp_fade_duration = overlap_fade_duration

        self.interval = interval
        self.mettatonize = mettatonize_gif
