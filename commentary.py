"""
Matching audio data to Statbomb events
"""
import enum
import dataclasses
import random
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


# TODO: add lookbehind to the conditions

CLIPS = (
    CommentaryClip(1, [event_type_is('Ball Receipt*'),
                       lambda x: random.random() > 0.05]),
    CommentaryClip(2, [event_type_is('Pass'),
                       lambda x: x.location[0] <= 40,  # starts in defensive third
                       lambda x: x.pass_.end_location[0] <= 60,  # ends in defensive half
                       lambda x: x.pass_.height.name == 'Ground Pass',
                       lambda x: x.pass_.outcome is None,  # is successful (NB: anything with a clarifying comment should just be a function)
                       ]),
    CommentaryClip(3, [event_type_is('Pass'),
                       lambda x: x.location[0] < 80,
                       lambda x: x.pass_.end_location[0] <= x.location[0],  # Backwards pass
                       lambda x: x.pass_.height.name == 'Ground Pass',
                       lambda x: x.pass_.outcome is None,
                       ]),
    CommentaryClip(5, [event_type_is('Pass'),
                       lambda x: x.location[0] <= 40,
                       lambda x: x.pass_.end_location[0] <= 40,
                       lambda x: x.pass_.outcome is None,
                       ]),


    CommentaryClip(17, [event_type_is('Pass'),
                        lambda x: x.location[0] <= 50,
                        lambda x: x.pass_.end_location[0] >= 60,
                        lambda x: x.pass_.length <= 20,
                        lambda x: x.pass_.height.name == 'Ground Pass',
                        lambda x: x.pass_.outcome is None,
                        ]),
    CommentaryClip(19, [event_type_is('Dribble'),
                        lambda x: x.dribble.outcome == 'Complete',
                        # lambda x: random.random() > 0.5,
                        ]),


    CommentaryClip(21, [event_type_is('Dribble'),  # NOTE: is carry more appropriate here?
                        lambda x: x.dribble.outcome == 'Complete',
                        # lambda x: random.random() > 0.5,
                        ]),
    CommentaryClip(24, [event_type_is('Dribble'),
                        lambda x: x.dribble.outcome == 'Complete',
                        # lambda x: random.random() > 0.5,
                        ]),
    CommentaryClip(25, [event_type_is('Pass'),
                        lambda x: x.location[0] < 80,
                        lambda x: x.pass_.end_location[0] <= x.location[0],  # Backwards pass
                        lambda x: x.pass_.height.name == 'Ground Pass',
                        lambda x: x.pass_.outcome is None,
                        ]),
    CommentaryClip(27, [event_type_is('Pass'),
                        # TODO: check if under pressure
                        lambda x: x.location[0] < 50,
                        lambda x: x.pass_.end_location[0] <= x.location[0],  # Backwards pass
                        lambda x: x.pass_.height.name == 'Ground Pass',
                        lambda x: x.pass_.outcome is None,
                        ]),

    CommentaryClip(35, [event_type_is('Ball Receipt*'),
                        # TODO: check if under pressure
                        lambda x: x.position.name == 'Goalkeeper',
                        lambda x: x.pass_.outcome is None,
                        ]),


    CommentaryClip(64, [event_type_is('Pass'),
                        lambda x: x.location[0] <= 80,
                        lambda x: x.pass_.end_location[0] >= 90,
                        lambda x: x.pass_.height.name == 'Ground Pass',
                        lambda x: x.pass_.outcome is None,
                        ]),


    CommentaryClip(143, [event_type_is('Ball Receipt*'),
                         lambda x: x.location[0] >= 80,
                         lambda x: 20 <= x.location[1] <= 60,
                         ]),
    CommentaryClip(144, [event_type_is('Ball Receipt*'),
                         lambda x: x.location[0] >= 80,
                         lambda x: 20 <= x.location[1] <= 60,
                         ]),

    CommentaryClip(148, [event_type_is('Ball Receipt*'),
                         lambda x: x.location[0] >= 80,
                         lambda x: 20 <= x.location[1] <= 60,
                         ]),

    CommentaryClip(175, [event_type_is('Shot'),
                         lambda x: x.shot.outcome == 'Goal',
                         ]),

)
