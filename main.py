import sys
import random
from typing import Optional

from PIL.Image import Image
from PIL.ImageFile import ImageFile
from pydub import AudioSegment
from PIL import Image, ImageSequence

def get_blip_timings_from_gif(gif_path: str) -> list[float]:
    gif: ImageFile = Image.open(gif_path)

    timings = []

    moment = 0
    prev_frame: Optional[Image] = None
    for frame in ImageSequence.Iterator(gif):
        moment += frame.info['duration']

        if prev_frame is None or frame.tobytes() != prev_frame.tobytes():
            timings.append(moment)

        prev_frame = frame.copy()

    return timings

def combine_audios(gif_path: str, *sound_paths: str) -> None:
    audios: list[AudioSegment] = []
    for sound_path in sound_paths:
        audios.append(AudioSegment.from_file(sound_path))

    max_sound_length = 0
    for audio in audios:
        if audio.duration_seconds > max_sound_length:
            max_sound_length = audio.duration_seconds

    blip_timings = get_blip_timings_from_gif(gif_path)
    final_blip_timing = blip_timings[len(blip_timings) - 1]

    print(final_blip_timing)
    print(max_sound_length)

    output = AudioSegment.silent(duration=final_blip_timing + (max_sound_length / 1000) + 0.15)
    for blip in blip_timings:
        output = output.overlay(random.choice(audios), position=blip)

    output.export("./test output/output.wav", format="wav")

def get_test_path(file_name: str) -> str:
    return f"./test input/{file_name}"


if __name__ == '__main__':
    combine_audios(get_test_path("flowey_helping.gif"), get_test_path("flowey.wav"))