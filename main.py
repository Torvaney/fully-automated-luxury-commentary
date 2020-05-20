import functools
import random
import typing

import pydub
import pydub.playback
import typer


class Event(typing.NamedTuple):
    end_time: float


def fetch_events(match_id: int, start: int, end: int) -> typing.List[Event]:
    return [
        Event(0.5),
        Event(1.5),
        Event(2.5),
        Event(4.5),
        Event(5.8),
        Event(10),
        Event(12.5),
    ]


def pick_commentary_clip(event: Event) -> pydub.AudioSegment:
    audio_id = random.randint(1, 472)
    try:
        return pydub.AudioSegment.from_wav(f'audio/chunks/chunk-{audio_id}.wav')
    except Exception:
        return pick_commentary_clip(event)


def join_commentary(x: typing.Tuple[Event, pydub.AudioSegment], y: typing.Tuple[Event, pydub.AudioSegment]) -> typing.Tuple[Event, pydub.AudioSegment]:
    # NOTE: It's a monad! Presumably we can simplify the code as a result?
    event1, audio1 = x
    event2, audio2 = y

    # We need to combine 2 audio clips while handling overlapping elegantly
    #
    # Imagine we have a timeline of events with variable duration, and some breaks
    # Events: e1--->      e2-->e3----->e4--------->  e5---->e6--->   etc
    #
    # In this program, each event is mapped to an audio clip of commentary that
    # should be played at the end of the event. Each audio clip also has a duration.
    # These audio clips are unlikely to be the exact right length of time, so
    # we must handle under and overlaps. If we go back to the timeline:
    # Events: e1--->      e2-->e3----->e4--------->  e5---->e6--->   etc
    # Audio:        a1------->
    #                          a2--------->
    #                                  a3------>
    #                                              a4----->
    #                                                       a5----> etc
    # In this (imagined) scenario, a2 and a3 overlap, while the rest of the audio
    # clips underlap.

    # So there are 2 scenarios that we need to handle
    # 1: Underlapping - This one is easy, we just fill in the time between audio
    #                   clips with silence.
    # 2: Overlapping  - There is no single correct approach in this case. For now,
    #                   we take the easy approach and simply remove any overlapped
    #                   audio. So in the example above, a3 would get removed and
    #                   the time between a2 and a4 is filled in with silence.
    #
    # (Of course, there is also the case where the audio clips are perfectly
    #  aligned to the microsecond. We treat this as an overlap.)

    time_to_next_event = event2.end_time - (event1.end_time + audio1.duration_seconds)
    if time_to_next_event > 0:
        # Underlap
        return (event1, audio1 + pydub.AudioSegment.silent(duration=time_to_next_event*1000) + audio2)

    # Else: Overlap
    # NOTE: We don't explicitly fill in the additional silence; this should get
    # filled in by further invocations of join_commentary, or by the final clipping
    return (event1, audio1)



def generate_commentary(events: typing.List[Event]) -> pydub.AudioSegment:
    _, audio = functools.reduce(join_commentary, [(e, pick_commentary_clip(e)) for e in events])
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
