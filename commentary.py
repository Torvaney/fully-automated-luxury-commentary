"""
Matching audio data to Statbomb events
"""
import dataclasses
import enum
import functools
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
        return all(f(event) or False for f in self.filters)


# Filters


class Composable:
    "Wrapper for composable single-argument function"
    def __init__(self, f=lambda x: x):
        self._f = f

    def __call__(self, x):
        return self._f(x)

    def __gt__(self, f):
        return Composable(lambda x: f(self._f(x)))

    def __lt__(self, f):
        return Composable(lambda x: self._f(f(x)))


isnt = Composable(lambda x: not x)


def event_type_is(event_type: str) -> Filter:
    return Composable(lambda x: x.type.name == event_type)


@Composable
def location(event: statsbombapi.Event) -> typing.Tuple[int, int]:
    return event.location


@Composable
def pass_end_location(event: statsbombapi.Event) -> typing.Tuple[int, int]:
    return event.pass_.end_location


def in_range(x_min: int=0, y_min: int=0, x_max: int=120, y_max: int=80) -> typing.Callable[[typing.Tuple[int, int]], bool]:
    return Composable(lambda xy: (x_min <= xy[0] < x_max) and (y_min <= xy[1] < y_max))


in_defensive_third = in_range(x_max=40)
in_defensive_half = in_range(x_max=60)
in_offensive_half = in_range(x_min=60)
in_offensive_third = in_range(x_min=80)


ground_pass = Composable(lambda x: x.pass_.height.name == 'Ground Pass')
successful_pass = Composable(lambda x: x.pass_.outcome is None)
backwards_pass = Composable(lambda x: pass_end_location(x)[0] < location(x)[0])


def with_weight(probability: float) -> Filter:
    return Composable(lambda x: random.random() < probability)


# Clips

# TODO: add lookbehind to the conditions

CLIPS = (
    CommentaryClip(1, [event_type_is('Ball Receipt*'), with_weight(0.05)]),
    CommentaryClip(2, [event_type_is('Pass'),
                       location > in_defensive_third,
                       pass_end_location > in_defensive_half,
                       ground_pass,
                       successful_pass]),
    CommentaryClip(3, [event_type_is('Pass'),
                       location > (isnt < in_offensive_third),
                       ground_pass,
                       successful_pass,
                       backwards_pass,]),
    CommentaryClip(5, [event_type_is('Pass'),
                       location > in_defensive_third,
                       pass_end_location > in_defensive_third,
                       successful_pass]),


    CommentaryClip(17, [event_type_is('Pass'),
                        location > in_range(x_max=50),  # Is this actually as readable as \x -> x <= 50?
                        location > in_range(x_min=60),
                        ground_pass,
                        successful_pass,
                        lambda x: x.pass_.length <= 20,
                        ]),
    CommentaryClip(19, [event_type_is('Dribble'),
                        lambda x: x.dribble.outcome.name == 'Complete',  #  OR dribble > outcome('Complete')
                        with_weight(0.5)]),


    CommentaryClip(21, [event_type_is('Dribble'),  # NOTE: is carry more appropriate here?
                        lambda x: x.dribble.outcome.name == 'Complete',
                        with_weight(0.5)]),
    CommentaryClip(24, [event_type_is('Dribble'),
                        lambda x: x.dribble.outcome.name == 'Complete',
                        with_weight(0.5)]),
    CommentaryClip(25, [event_type_is('Pass'),
                        location > (isnt < in_offensive_third),
                        backwards_pass,
                        successful_pass]),
    CommentaryClip(27, [event_type_is('Pass'),
                        # TODO: check if under pressure
                        location > in_defensive_half,
                        backwards_pass,
                        ground_pass,
                        successful_pass]),


    CommentaryClip(35, [event_type_is('Ball Receipt*'),
                        # TODO: check if under pressure
                        lambda x: x.position.name == 'Goalkeeper']),


    CommentaryClip(64, [event_type_is('Pass'),
                        location > (isnt < in_offensive_third),
                        lambda x: pass_end_location(x)[0] >= 90,
                        ground_pass,
                        successful_pass]),


    CommentaryClip(143, [event_type_is('Ball Receipt*'),
                         lambda x: location(x)[0] >= 100,
                         lambda x: 20 <= location(x)[1] <= 60]),
    CommentaryClip(144, [event_type_is('Ball Receipt*'),
                         lambda x: location(x)[0] >= 100,
                         lambda x: 20 <= location(x)[1] <= 60]),

    CommentaryClip(148, [event_type_is('Ball Receipt*'),
                         lambda x: location(x)[0] >= 100,
                         lambda x: 20 <= location(x)[1] <= 60]),

    CommentaryClip(175, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal']),
    CommentaryClip(194, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.01]),
    CommentaryClip(197, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.01]),
    CommentaryClip(199, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.20,
                         lambda x: x.shot.statsbomb_xg2 >= 0.60]),


    CommentaryClip(203, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.20,
                         lambda x: x.shot.statsbomb_xg2 >= 0.60]),


    CommentaryClip(211, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal']),


    CommentaryClip(229, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal']),


    CommentaryClip(235, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.one_on_one]),


    CommentaryClip(241, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.one_on_one]),


    CommentaryClip(341, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(345, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(349, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(353, [event_type_is('Shot'),
                         location > in_range(max_x=95),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(358, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(362, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(366, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(367, [event_type_is('Shot'),
                         lambda x: x.shot.statsbomb_xg > 0.15,
                         lambda x: x.shot.outcome.name == 'Off T']),


    CommentaryClip(389, [event_type_is('Shot'),
                         lambda x: x.shot.statsbomb_xg2 > 0.15,
                         lambda x: x.shot.outcome.name == 'Saved']),


    CommentaryClip(398, [event_type_is('Shot'),
                         lambda x: x.shot.statsbomb_xg2 <= 0.15,
                         lambda x: x.shot.outcome.name == 'Saved']),


    # Throw ins
    CommentaryClip(402, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(403, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(404, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(407, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(408, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(411, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),
    CommentaryClip(414, [event_type_is('Pass'),
                         lambda x: x.pass_.outcome.name == 'Out']),

    # Fouls
    CommentaryClip(418, [event_type_is('Foul Committed')]),
    CommentaryClip(419, [event_type_is('Foul Committed')]),
    CommentaryClip(420, [event_type_is('Foul Committed')]),
    CommentaryClip(423, [event_type_is('Foul Committed')]),
    CommentaryClip(425, [event_type_is('Foul Committed')]),
    CommentaryClip(427, [event_type_is('Foul Committed')]),


    # Great expectancy!
    CommentaryClip(434, [location > in_range(x_min=100, y_min=30, y_max=50)]),

)
