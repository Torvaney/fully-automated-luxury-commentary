import functools
import os
import random
import typing

import pydub
import pydub.playback
import statsbombapi
import typer

import commentary


class EventCommentary(typing.NamedTuple):
    """ A StatsBomb event paired with a commentary clip. """
    event: statsbombapi.Event
    audio: pydub.AudioSegment


def start_time(event: statsbombapi.Event) -> int:
    return event.minute*60 + event.second


def end_time(event: statsbombapi.Event) -> int:
    return start_time(event) + (event.duration or 0)


def clip_time(event: statsbombapi.Event) -> int:
    return start_time(event)


def pad_audio(audio: pydub.AudioSegment, padding_before: int=0, padding_after: int=0) -> pydub.AudioSegment:
    return (
        pydub.AudioSegment.silent(max(0, padding_before)*1000) +
        audio +
        pydub.AudioSegment.silent(max(0, padding_after)*1000)
    )


def fetch_events(match_id: int, start: int, end: int) -> typing.List[statsbombapi.Event]:
    api = statsbombapi.StatsbombPublic()
    all_events = api.events(match_id=match_id)
    return [e for e in all_events if (start <= start_time(e)) and (end_time(e) <= end)]


def load_clip(clip_id: int) -> pydub.AudioSegment:
    path_to_clip = os.path.join(os.path.dirname(__file__), 'audio', f'chunk-{clip_id}.wav')
    return pydub.AudioSegment.from_wav(path_to_clip)


def pick_commentary_clip(event: statsbombapi.Event) -> typing.Optional[pydub.AudioSegment]:
    matching_clips = [c for c in commentary.CLIPS if c.match(event)]
    if len(matching_clips) == 0:
        return None
    selected_clip = random.choice(matching_clips)
    print(f'Selected {selected_clip.clip_id} for {event.type.name} @ ({event.minute}, {event.second})')
    return load_clip(selected_clip.clip_id)


def join_commentary(x: EventCommentary, y: EventCommentary) -> EventCommentary:
    # NOTE: It's a monad? Presumably we can simplify the code as a result?
    event1, audio1 = x
    event2, audio2 = y

    audio1 = audio1 or pydub.AudioSegment.silent(duration=0)
    audio2 = audio2 or pydub.AudioSegment.silent(duration=0)

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

    time_to_next_event = clip_time(event2) - (clip_time(event1) + audio1.duration_seconds)
    if time_to_next_event > 0:
        # Underlap
        if y.audio:
            print(f'Joining clips for {event1.type.name} @ ({event1.minute}, {event1.second})->{audio1.duration_seconds:.2f} and {event2.type.name} @ ({event2.minute}, {event2.second})')
        return EventCommentary(event1, audio1 + pydub.AudioSegment.silent(duration=time_to_next_event*1000) + audio2)

    # Overlap
    # NOTE: We don't explicitly fill in the additional silence; this should get
    # filled in by further invocations of join_commentary, or by the final clipping
    if y.audio:
        print(f'Skipping overlapping clip for {event2.type.name} @ ({event2.minute}, {event2.second})')
        print(f'\t Event starts at ({event2.minute}, {event2.second}) - previous event ends at ({event1.minute}, {event1.second})-> {audio1.duration_seconds:.2f}')
    return EventCommentary(event1, audio1)


def generate_commentary(events: typing.List[statsbombapi.Event]) -> EventCommentary:
    events_with_commentary = [EventCommentary(e, pick_commentary_clip(e)) for e in events]
    return functools.reduce(join_commentary, [e for e in events_with_commentary if e.audio])


def main(match_id: int, start: int, end: int, audio_out: typing.Optional[str]=None, play: bool=False):
    # Fetch events from the statbomb API
    typer.echo(f'Fetching events for match {match_id} between {start}s and {end}s...')
    events = fetch_events(match_id, start, end)

    # Map event->audio and concatenate together
    typer.echo(f'Generating commentary...')
    init_event, audio = generate_commentary(events)

    # Fill any time at the start or end of the clip
    time_to_start = clip_time(init_event) - start
    time_remaining = (end-start) - (audio.duration_seconds+time_to_start)
    audio = pad_audio(audio, time_to_start, time_remaining)

    default_audio_out = f'{match_id}-{start}-{end}.wav'
    typer.echo(f'Writing audio file to {audio_out or default_audio_out}...')
    audio.export(audio_out or default_audio_out, format='wav')

    if play:
        pydub.playback.play(audio)

    typer.echo('All done!')


if __name__ == "__main__":
    typer.run(main)
