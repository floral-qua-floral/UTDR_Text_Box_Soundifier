import os
import random
import sys
from typing import Optional

from PIL.Image import Image
from PIL.ImageFile import ImageFile
from pydub import AudioSegment
from PIL import Image, ImageSequence

from settings import SoundifierSettings

def get_blip_timings_from_gif(gif_path: str, settings: SoundifierSettings) -> list[int]:
    gif: ImageFile = Image.open(gif_path)

    prev_frame: Optional[Image] = None

    frame_count = 0
    last_changing_frame = 0
    consecutive_identical_frames = 0

    frames_before_pauses = []
    frames_after_pauses = []

    for frame in ImageSequence.Iterator(gif):
        frame_count += 1
        if prev_frame is None or frame.tobytes() != prev_frame.tobytes():
            last_changing_frame = frame_count
            if consecutive_identical_frames >= 2:
                frames_after_pauses.append(frame_count)
            consecutive_identical_frames = 0
        else:
            consecutive_identical_frames += 1
            if consecutive_identical_frames == 2:
                frames_before_pauses.append(frame_count - 2)

        prev_frame = frame.copy()

    moment = 0
    letter_changes = 0
    timings = []

    frame_number = 0
    metta_letters = 0
    accumulated_frame_duration = 0
    frames = []
    durations = []

    for frame in ImageSequence.Iterator(gif):
        moment += frame.info['duration']
        frame_number += 1

        frame_natural_duration = frame.info['duration']
        accumulated_frame_duration += frame_natural_duration / settings.speed

        frame_changed = prev_frame is None or frame.tobytes() != prev_frame.tobytes()

        if frame_number in frames_after_pauses:
            letter_changes = 0

        about_to_pause = frame_number in frames_before_pauses

        if frame_changed:
            letter_changes += 1

            metta_letters += 1
            consecutive_identical_frames = 0

            if letter_changes % settings.interval == 0 or about_to_pause:
                timings.append(moment / settings.speed)
        else:
            if consecutive_identical_frames >= 2:
                metta_letters = 0
            else:
                metta_letters += 1
            consecutive_identical_frames += 1

        skip_rendering_frame = settings.mettatonize and metta_letters % settings.interval != 0 and frame_number < last_changing_frame and not about_to_pause

        if not skip_rendering_frame:
            frames.append(frame.copy())
            durations.append(accumulated_frame_duration)
            accumulated_frame_duration = 0

        prev_frame = frame.copy()

    if settings.output_gif_path is not None:
        frames[0].save(
            settings.output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=durations,
            loop=gif.info['loop'],
            disposal=2
        )
        print(f"Successfully saved speed-altered gif as {settings.output_gif_path}")

    return timings

def insert_blip(
        insert_in: AudioSegment,
        voices: list[AudioSegment],
        this_blip: int, next_blip: int,
        settings: SoundifierSettings
) -> AudioSegment:
    voice: AudioSegment = random.choice(voices)

    if settings.do_overlap_prevention:
        voice = ((AudioSegment.silent(duration=next_blip - this_blip + settings.olp_hard_cutoff_leniency))
                .overlay(voice).fade_out(duration=settings.olp_fade_duration))

    return insert_in.overlay(voice, position=this_blip)

def make_blip_track(gif: str, settings: SoundifierSettings, *sound_paths: str) -> AudioSegment:
    if len(sound_paths) == 1 and "#" in sound_paths[0] and not os.path.isfile(sound_paths[0]):
        index: int
        if os.path.isfile(sound_paths[0].replace("#", "0")):
            index = 0
        else:
            index = 1

        numerated_paths: list[str] = []

        while True:
            checking_path = sound_paths[0].replace("#", str(index))
            if not os.path.isfile(checking_path): break
            index += 1
            numerated_paths.append(checking_path)

        return make_blip_track(gif, settings, *numerated_paths)

    audios: list[AudioSegment] = []
    for sound_path in sound_paths:
        audios.append(AudioSegment.from_file(sound_path))

    max_sound_length = 0
    for audio in audios:
        if audio.duration_seconds > max_sound_length:
            max_sound_length = audio.duration_seconds

    blip_timings = get_blip_timings_from_gif(gif, settings)
    final_blip_timing = blip_timings[len(blip_timings) - 1]

    total_duration = (final_blip_timing + (max_sound_length * 1000) + 150)
    output = AudioSegment.silent(duration=total_duration)
    for index in range(len(blip_timings)):
        blip = blip_timings[index]

        next_blip: int
        if index == len(blip_timings) - 1:
            next_blip = total_duration
        else:
            next_blip = blip_timings[index + 1]

        output = insert_blip(output, audios, blip, next_blip, settings)

    return output

def save_blip_track(settings: SoundifierSettings, audio: AudioSegment) -> None:
    audio.export(settings.output_audio_path, format="wav")
    print(f"Successfully saved audio as {settings.output_audio_path}")

def make_and_save_blip_track(gif: str, settings: SoundifierSettings, *sound_paths: str) -> None:
    save_blip_track(settings, make_blip_track(gif, settings, *sound_paths))

if __name__ == '__main__':
    args: list[str] = sys.argv[1:]
    if len(args) == 0:
        args.append("./test input/typer.gif")
        args.append("./test voices/typer.wav")

    voice_paths: list[str] = []
    path_of_gif: str = ""
    for path in args:
        if path[len(path) - 4:] == ".gif":
            path_of_gif = path
        if path[len(path) - 4:] == ".wav":
            voice_paths.append(path)

    if len(voice_paths) == 0:
        raise Exception("No voices provided!")
    if path_of_gif == "":
        raise Exception("No gif provided!")

    make_and_save_blip_track(path_of_gif, SoundifierSettings("./test output/output.wav", speed=1, output_gif_path="./test output/output.gif"), *voice_paths)