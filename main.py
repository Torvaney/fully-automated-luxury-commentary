import functools
import typing

import pydub
import pydub.playback
import typer


class Event:
    pass


def TODO(*args, **kwargs):
    raise NotImplementedError(f'TODO {args}, {kwargs}')


def fetch_events(match_id: int, start: int, end: int) -> typing.List[Event]:
    return [
        1, 2, 3
    ]


def pick_commentary_clip(event: Event) -> pydub.AudioSegment:
    return pydub.AudioSegment.from_wav('audio/chunks/chunk-32.wav')


def generate_commentary(events: typing.List[Event]) -> pydub.AudioSegment:
    # map (Event -> (Event, Audio))
    # reduce ... -- NB we need some way to stop clips overlapping

    audio = functools.reduce(
        lambda x, y: x + y,
        [pick_commentary_clip(e) for e in events]
    )
    return audio


def main(match_id: int, start: int, end: int, audio_out: typing.Optional[str]=None, play: bool=False):
    # Fetch events from the statbomb API
    typer.echo(f'Fetching events for match {match_id} between {start}s and {end}s...')
    events = fetch_events(match_id, start, end)

    # Map event->audio and concatenate together
    typer.echo(f'Generating commentary...')
    audio = generate_commentary(events)

    default_audio_out = f'{match_id}-{start}-{end}.wav'
    typer.echo(f'Writing audio file to {audio_out or default_audio_out}...')
    audio.export(audio_out or default_audio_out, format='wav')

    if play:
        pydub.playback.play(audio)

    typer.echo('All done!')


if __name__ == "__main__":
    typer.run(main)
