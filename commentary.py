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
        return all(f(event) for f in self.filters)


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


def in_range(x_min: int=0, y_min: int=0, x_max: int=121, y_max: int=81) -> typing.Callable[[typing.Tuple[int, int]], bool]:
    return Composable(lambda xy: (x_min <= xy[0] < x_max) and (y_min <= xy[1] < y_max))


in_defensive_third = in_range(x_max=40)
in_defensive_half = in_range(x_max=60)
in_offensive_half = in_range(x_min=60)
in_offensive_third = in_range(x_min=80)


ground_pass = Composable(lambda x: x.pass_.height.name == 'Ground Pass')
backwards_pass = Composable(lambda x: pass_end_location(x)[0] < (location(x)[0] - 5))
successful_pass = Composable(lambda x: x.pass_.outcome is None)


def comment(x):
    return lambda x: True


def todo(x):
    return lambda x: False


def pass_outcome(name):
    return Composable(lambda x: x.pass_.outcome.name == name if x.pass_.outcome else None)


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
                       successful_pass,
                       with_weight(0.05)]),
    CommentaryClip(3, [event_type_is('Pass'),
                       location > (isnt < in_offensive_third),
                       ground_pass,
                       successful_pass,
                       backwards_pass,
                       with_weight(0.1)]),
    CommentaryClip(5, [event_type_is('Pass'),
                       location > in_defensive_third,
                       pass_end_location > in_defensive_third,
                       successful_pass,
                       with_weight(0.1)]),
    CommentaryClip(6, [event_type_is('Pass'),
                       todo('Chance now for a counter attack - need lookbehind'),]),
    CommentaryClip(9, [event_type_is('Pass'),
                       todo('Turnover deep in defensive zone - need lookbehind'),]),
    CommentaryClip(10, [event_type_is('Pass'),
                        comment('A chance now to build from the back'),
                        location > in_defensive_third,
                        successful_pass,
                        lambda x: x.pass_.length <= 20,
                        with_weight(0.1)]),
    CommentaryClip(12, [event_type_is('Pass'),
                        todo('A lovely series of passes now - need lookbehind'),]),
    CommentaryClip(14, [event_type_is('Pass'),
                        todo('Passing well in their own half - same as previous'),]),
    CommentaryClip(16, [event_type_is('Pass'),
                        todo('Confident stuff in defence'),]),
    CommentaryClip(17, [event_type_is('Pass'),
                        comment('Now they can press forward'),
                        location > in_range(x_max=50),  # Is this actually as readable as lambda x: x <= 50?
                        pass_end_location > in_range(x_min=60),
                        ground_pass,
                        successful_pass,
                        lambda x: x.pass_.length <= 20,
                        with_weight(0.2)]),
    CommentaryClip(19, [event_type_is('Dribble'),
                        comment('Good Skill!'),
                        lambda x: x.dribble.outcome.name == 'Complete',  #  OR dribble > outcome('Complete')
                        with_weight(0.5)]),
    CommentaryClip(20, [event_type_is('Dribble'),
                        comment('Needs to find someone to pass to here...'),
                        lambda x: x.dribble.outcome.name == 'Complete',
                        with_weight(0.5)]),
    CommentaryClip(21, [event_type_is('Dribble'),  # NOTE: is carry more appropriate here?
                        comment('He\'s not afraid to hold onto the ball...'),
                        lambda x: x.dribble.outcome.name == 'Complete',
                        with_weight(0.5)]),
    CommentaryClip(24, [event_type_is('Dribble'),
                        comment('Great control!'),
                        lambda x: x.dribble.outcome.name == 'Complete',
                        with_weight(0.5)]),

    CommentaryClip(25, [event_type_is('Pass'),
                        comment('And a good attempt to slow the pace down'),
                        location > (isnt < in_offensive_third),
                        backwards_pass,
                        successful_pass,
                        with_weight(0.05)]),
    CommentaryClip(27, [event_type_is('Pass'),
                        comment('That was a sensible backpass!'),
                        # TODO: check if under pressure
                        # TODO: check that it's received by GK?
                        location > in_defensive_half,
                        backwards_pass,
                        ground_pass,
                        successful_pass,
                        with_weight(0.1)]),
    CommentaryClip(29, [event_type_is('Pass'),
                        comment('Good idea - but there was no way forward'),
                        location > (isnt < in_offensive_third),
                        pass_end_location > in_offensive_third,
                        ground_pass,
                        (isnt < successful_pass)]),
    CommentaryClip(31, [todo('No option available to him...'),]),
    CommentaryClip(32, [todo('The crowd aren\'t very happy with that!'),]),

    CommentaryClip(33, [event_type_is('Ball Receipt*'),
                        # TODO: check if pass was under pressure
                        lambda x: x.position.name == 'Goalkeeper']),
    CommentaryClip(35, [event_type_is('Ball Receipt*'),
                        lambda x: x.position.name == 'Goalkeeper']),
    CommentaryClip(38, [event_type_is('Ball Receipt*'),
                        comment('And that\'s a bit negative'),
                        lambda x: x.position.name == 'Goalkeeper']),

    CommentaryClip(40, [event_type_is('Pass'),
                        comment('That\'s a long ball forward'),
                        location > in_defensive_third,
                        pass_end_location > in_offensive_third]),
    CommentaryClip(44, [event_type_is('Pass'),
                        comment('It goes straight up the field'),
                        location > in_defensive_third,
                        pass_end_location > in_offensive_third]),
    CommentaryClip(46, [event_type_is('Pass'),
                        comment('A defence-splitting ball!'),
                        lambda x: x.pass_.technique.name == 'Through Ball']),
    CommentaryClip(48, [event_type_is('Pass'),
                        todo('That\'s not very long'),]),

    CommentaryClip(49, [event_type_is('Pass'),
                        comment('Great vision by the goalkeeper'),
                        successful_pass,
                        pass_end_location > in_offensive_third,
                        lambda x: x.position.name == 'Goalkeeper',]),
    CommentaryClip(50, [event_type_is('Shot'),
                        comment('The goalkeeper bails out his defence'),
                        lambda x: x.shot.outcome.name == 'Saved',]),
    CommentaryClip(52, [event_type_is('Shot'),
                        comment('The goalkeeper reads the situation very well, indeed'),
                        lambda x: x.shot.outcome.name == 'Saved',]),
    CommentaryClip(53, [todo('Is this sensible I wonder?'),
                        lambda x: x.position.name == 'Goalkeeper',]),
    CommentaryClip(54, [todo('Well he\'d better find someone to pass it to here'),
                        lambda x: x.position.name == 'Goalkeeper',]),
    CommentaryClip(55, [comment('And the goalkeeper is out of his penalty area, here!'),
                        event_type_is('Carry'),
                        lambda x: x.position.name == 'Goalkeeper',
                        location > in_range(x_min=24)]),
    CommentaryClip(55, [comment('That\'s a bit risky'),
                        event_type_is('Carry'),
                        lambda x: x.position.name == 'Goalkeeper',
                        location > in_range(x_min=24)]),

    CommentaryClip(60, [todo('Now they\'re really pushing forward')]),
    CommentaryClip(61, [todo('And the midfielders really take control')]),
    CommentaryClip(63, [todo('Now - what can they do from here?'),
                        event_type_is('Pass'),
                        location > (isnt < in_offensive_third),
                        pass_end_location > in_offensive_third,
                        ground_pass,
                        successful_pass]),
    CommentaryClip(64, [event_type_is('Pass'),
                        comment('Here\'s the pass into the danger area'),
                        location > (isnt < in_range(x_min=100, y_min=20, y_max=60)),
                        pass_end_location > in_range(x_min=100, y_min=20, y_max=60),
                        successful_pass]),
    CommentaryClip(65, [event_type_is('Pass'),
                        comment('Will anyone get on the end of this one?'),
                        location > (isnt < in_range(x_min=100, y_min=20, y_max=60)),
                        pass_end_location > in_range(x_min=100, y_min=20, y_max=60),
                        successful_pass]),
    CommentaryClip(66, [event_type_is('Pass'),
                        comment('That\'s a long pass'),
                        location > in_defensive_third,
                        pass_end_location > in_offensive_third]),
    CommentaryClip(66, [event_type_is('Pass'),
                        comment('Can they split the opponents defence'),
                        location > in_defensive_third,
                        pass_end_location > in_offensive_third]),

    CommentaryClip(70, [event_type_is('Dribble'),
                        comment('Nice, close control'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),
    CommentaryClip(72, [event_type_is('Dribble'),
                        comment('He is not afraid to take players on'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),
    CommentaryClip(74, [event_type_is('Dribble'),
                        comment('He is creating some space in midfield, here'),
                        location > (isnt < in_defensive_third),
                        location > (isnt < in_offensive_third),
                        lambda x: x.dribble.outcome.name == 'Complete',]),
    CommentaryClip(75, [event_type_is('Dribble'),
                        comment('Look at his control!'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),
    CommentaryClip(76, [event_type_is('Dribble'),
                        comment('And off he goes!'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),

    CommentaryClip(77, [event_type_is('Ball Receipt*'),
                        comment('Will he go all the way on his own?'),
                        location > (isnt < in_defensive_third)]),
    CommentaryClip(78, [event_type_is('Dribble'),
                        comment('He looks unstoppable!'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),
    CommentaryClip(79, [event_type_is('Dribble'),
                        comment('He\'s taking them all on!'),
                        lambda x: x.dribble.outcome.name == 'Complete',]),

    CommentaryClip(80, [event_type_is('Dribble'),
                        comment('He leads the attack from the left hand side'),
                        location > in_range(y_max=30),]),
    CommentaryClip(81, [event_type_is('Ball Receipt*'),
                        comment('They are trying to find a way in from the left here'),
                        location > in_offensive_third,
                        location > in_range(y_max=30),]),
    CommentaryClip(83, [event_type_is('Pass'),
                        comment('Here they come over the left hand side'),
                        location > in_offensive_third,
                        location > in_range(y_max=30),
                        pass_end_location > (isnt < in_offensive_third)]),
    CommentaryClip(84, [event_type_is('Dribble'),
                        comment('Great flank play, here'),
                        location > (isnt < in_range(y_min=20, y_max=60)),
                        lambda x: x.dribble.outcome.name == 'Complete']),

    CommentaryClip(85, [event_type_is('Dribble'),
                        comment('Yes, he is trying to make the run through the middle'),
                        location > in_range(y_min=20, y_max=60),
                        location > (isnt < in_defensive_third),]),
    CommentaryClip(88, [event_type_is('Dribble'),
                        comment('Well, the space is there!'),
                        location > in_range(y_min=20, y_max=60),
                        location > (isnt < in_defensive_third),
                        lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(90, [event_type_is('Dribble'),
                        comment('Yes, bold stuff'),
                        location > in_range(y_min=20, y_max=60),
                        location > in_defensive_third,
                        lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(92, [event_type_is('Dribble'),
                        comment('Straight through the middle!'),
                        location > in_range(y_min=20, y_max=60),
                        location > (isnt < in_defensive_third),
                        lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(95, [event_type_is('Dribble'),
                        comment('He\'s cutting a path right through the middle now!'),
                        location > in_range(y_min=20, y_max=60),
                        location > (isnt < in_defensive_third),
                        lambda x: x.dribble.outcome.name == 'Complete']),

    CommentaryClip(96, [event_type_is('Ball Receipt*'),
                        comment('They are trying to find a way in from the right'),
                        location > in_offensive_third,
                        location > in_range(y_min=50),]),
    CommentaryClip(99, [event_type_is('Dribble'),
                        comment('He uses the space on the right nicely'),
                        location > in_range(y_min=50),
                        lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(101, [event_type_is('Pass'),
                         comment('Here they come on the right'),
                         location > (isnt < in_offensive_third),
                         pass_end_location > in_range(y_min=50),
                         pass_end_location > in_offensive_third,
                         successful_pass,]),
    CommentaryClip(103, [event_type_is('Pass'),
                         comment('Space here on the right'),
                         location > (isnt < in_offensive_third),
                         pass_end_location > in_range(y_min=50),
                         pass_end_location > in_offensive_third,
                         successful_pass,]),

    CommentaryClip(104, [todo('And they are really putting the pressure on now')]),
    CommentaryClip(106, [todo('They are looking desperately for a way through')]),
    CommentaryClip(108, [event_type_is('Pass'),
                         lambda x: x.pass_.technique.name == 'Through Ball']),
    CommentaryClip(109, [todo('They are certainly having to be patient!')]),
    CommentaryClip(110, [todo('Here\'s a chance to hit them on the break')]),
    CommentaryClip(111, [event_type_is('Dispossessed'),]),
    CommentaryClip(112, [todo('They could be punished on the counter attack')]),
    CommentaryClip(113, [event_type_is('Miscontrol')]),
    CommentaryClip(114, [todo('And the break is on')]),
    CommentaryClip(115, [todo('Here comes the counter thrust')]),

    CommentaryClip(117, [todo('And he\'s looking to hoist one in from there')]),
    CommentaryClip(119, [todo('He has made himself enough space to create some danger here')]),
    CommentaryClip(121, [todo('He will be looking to pinpoint someone in the box')]),
    CommentaryClip(122, [todo('Can he pierce the defence now!')]),
    CommentaryClip(123, [comment('Is there anyone on the end of it!'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.technique.name == 'Through Ball']),
    CommentaryClip(125, [comment('This looks dangerous'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.technique.name == 'Through Ball',
                         successful_pass]),
    CommentaryClip(126, [todo('And he cuts inside...')]),
    CommentaryClip(127, [todo('Well they are all waiting for a possible pass')]),
    CommentaryClip(129, [comment('And he puts a cross into the danger area...'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross]),
    CommentaryClip(130, [comment('He\'s managed to lift one into the center...'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross]),
    CommentaryClip(131, [comment('Past the defender, now...'),
                         event_type_is('Dribble'),
                         location > in_offensive_third,
                         successful_pass,]),
    CommentaryClip(132, [comment('Here comes the cross from the left'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross,
                         location > in_range(y_max=30),]),
    CommentaryClip(133, [comment('Oh, useful cross'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross,
                         location > in_range(y_max=30),
                         successful_pass]),
    CommentaryClip(134, [comment('That is a good ball from the right'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross,
                         location > in_range(y_min=50),
                         successful_pass]),
    CommentaryClip(135, [comment('This could cause problems for the defence'),
                         event_type_is('Dribble'),
                         location > in_offensive_third,
                         successful_pass,]),
    CommentaryClip(134, [comment('He whips it in from the right'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross,
                         location > in_range(y_min=50)]),
    CommentaryClip(84, [event_type_is('Dribble'),
                        comment('Great wing play'),
                        location > (isnt < in_range(y_min=20, y_max=60)),
                        lambda x: x.dribble.outcome.name == 'Complete']),

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
                         location > in_range(x_max=95),
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
                         lambda x: x.shot.outcome.name == 'Saved',
                         lambda x: x.shot.statsbomb_xg2 and x.shot.statsbomb_xg2 > 0.15]),


    CommentaryClip(398, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Saved',
                         lambda x: x.shot.statsbomb_xg2 and x.shot.statsbomb_xg2 <= 0.15]),


    # Throw ins
    # TODO: check that it goes out off the *side* of the pitch
    CommentaryClip(402, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(403, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(404, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(407, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(408, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(411, [event_type_is('Pass'), pass_outcome('Out')]),
    CommentaryClip(414, [event_type_is('Pass'), pass_outcome('Out')]),

    # Fouls
    CommentaryClip(418, [event_type_is('Foul Committed')]),
    CommentaryClip(419, [event_type_is('Foul Committed')]),
    CommentaryClip(420, [event_type_is('Foul Committed')]),
    CommentaryClip(423, [event_type_is('Foul Committed')]),
    CommentaryClip(425, [event_type_is('Foul Committed')]),
    CommentaryClip(427, [event_type_is('Foul Committed')]),


    # Great expectancy!
    CommentaryClip(434, [event_type_is('Ball Receipt*'),
                         location > in_range(x_min=100, y_min=30, y_max=50)]),

)
