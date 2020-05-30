"""
Matching audio data to Statbomb events
"""
import enum
import dataclasses
import typing

import statsbombapi


# TODO: figure out a nice way to defunctionalise the filters
# Needs to be a recursive tree where type constructors = And a a | Or a a | Leaf a
Filter = typing.Callable[[statsbombapi.Event], bool]


class CommentaryClip(typing.NamedTuple):
    clip_id: int
    filters: typing.List[Filter]

    def match(self, event: statsbombapi.Event) -> bool:
        return all(f(event) for f in self.filters)


def event_type_is(event_type: str) -> Filter:
    return lambda x: x.type.name == event_type


CLIPS = (
    CommentaryClip(1, [event_type_is('Ball Receipt*'),
                       lambda x: not x.miscontrol]),
    CommentaryClip(2, [event_type_is('Pass'),
                       lambda x: x.location[0] <= 40,  # starts in defensive third
                       lambda x: x.pass_.end_location[0] <= 60,  # ends in defensive half
                       lambda x: x.pass_.height.name == 'Ground Pass',
                       lambda x: x.pass_.outcome is None,  # is successful (NB: anything with a clarifying comment should just be a function)
                       ]),
    CommentaryClip(3, [event_type_is('Pass'),
                       lambda x: x.pass_.end_location[0] <= x.location[0],  # Backwards pass
                       lambda x: x.pass_.height.name == 'Ground Pass',
                       lambda x: x.pass_.outcome is None,
                       ]),
    CommentaryClip(5, [event_type_is('Pass'),
                       lambda x: x.location[0] <= 40,
                       lambda x: x.pass_.end_location[0] <= 40,
                       lambda x: x.pass_.outcome is None,
                       ]),

)