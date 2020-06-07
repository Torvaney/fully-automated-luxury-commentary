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
        try:
            return all(f(event) for f in self.filters)
        except Exception as err:
            raise Exception(f'Threw error while matching clip {self.clip_id}') from err


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
through_ball = Composable(lambda x: x.pass_.technique and x.pass_.technique.name == 'Through Ball')


def xg2_at_least(value, default=True):
    @Composable
    def f(x):
        if x.shot.statsbomb_xg2 and x.shot.statsbomb_xg2 >= value:
            return True
        return default
    return f


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
                        through_ball]),
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

    CommentaryClip(77, [event_type_is('Pass'),
                        comment('Will he go all the way on his own?'),
                        location > (isnt < in_offensive_third),
                        pass_end_location > in_offensive_third]),
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
                        location > in_range(y_min=60),]),
    CommentaryClip(99, [event_type_is('Dribble'),
                        comment('He uses the space on the right nicely'),
                        location > in_range(y_min=60),
                        lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(101, [event_type_is('Pass'),
                         comment('Here they come on the right'),
                         location > (isnt < in_offensive_third),
                         pass_end_location > in_range(y_min=60),
                         pass_end_location > in_offensive_third,
                         successful_pass,]),
    CommentaryClip(103, [event_type_is('Pass'),
                         comment('Space here on the right'),
                         location > (isnt < in_offensive_third),
                         pass_end_location > in_range(y_min=60),
                         pass_end_location > in_offensive_third,
                         successful_pass,]),

    CommentaryClip(104, [todo('And they are really putting the pressure on now')]),
    CommentaryClip(106, [todo('They are looking desperately for a way through')]),
    CommentaryClip(108, [event_type_is('Pass'), through_ball]),
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
                         event_type_is('Pass'), through_ball]),
    CommentaryClip(125, [comment('This looks dangerous'),
                         event_type_is('Pass'), through_ball,
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
                         location > in_offensive_third,]),
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
                         location > in_offensive_third,]),
    CommentaryClip(136, [comment('He whips it in from the right'),
                         event_type_is('Pass'),
                         lambda x: x.pass_.cross,
                         location > in_range(y_min=50)]),
    CommentaryClip(137, [event_type_is('Dribble'),
                         comment('Great wing play'),
                         location > (isnt < in_range(y_min=20, y_max=60)),
                         lambda x: x.dribble.outcome.name == 'Complete']),

    CommentaryClip(139, [event_type_is('Pass'),
                         comment('A perfectly weighted long ball'),
                         location > in_defensive_third,
                         pass_end_location > in_offensive_third,
                         successful_pass]),
    CommentaryClip(140, [event_type_is('Pass'),
                         comment('And they have syncronised well'),
                         location > in_defensive_third,
                         pass_end_location > in_offensive_third,
                         successful_pass]),

    CommentaryClip(141, [event_type_is('Shot'),
                         comment('He has a crack at goal!'),]),
    CommentaryClip(142, [event_type_is('Shot'),
                         comment('He lets this one fly from distance!'),
                         location > in_range(x_max=100)]),
    CommentaryClip(143, [event_type_is('Ball Receipt*'),
                         comment('He has a sight of goal now'),
                         location > in_range(x_min=100, y_min=20, y_max=60)]),
    CommentaryClip(144, [event_type_is('Ball Receipt*'),
                         comment('He does have room for a shot!'),
                         location > in_range(x_min=100, y_min=20, y_max=60)]),
    CommentaryClip(145, [event_type_is('Shot'),
                         comment('And the danger subsides...!'),
                         lambda x: x.shot.outcome.name in ['Wayward', 'Off T']]),
    CommentaryClip(146, [event_type_is('Shot'),
                         comment('Good defending'),
                         lambda x: x.shot.outcome.name == 'Blocked']),
    CommentaryClip(147, [event_type_is('Clearance'),
                         comment('And they have repelled that raid'),]),
    CommentaryClip(148, [event_type_is('Ball Receipt*'),
                         comment('Must shoot from here'),
                         location > in_range(x_min=105, y_min=20, y_max=60),]),
    CommentaryClip(149, [event_type_is('Ball Receipt*'),
                         comment('It is a great position for a shot'),
                         location > in_range(x_min=100, y_min=20, y_max=60),]),
    CommentaryClip(151, [event_type_is('Shot'),
                         comment('He must score from here'),
                         lambda x: x.shot.statsbomb_xg >= 0.7]),
    CommentaryClip(152, [event_type_is('Pass'),
                         comment('Is this the vital opening?'),
                         location > (isnt < in_range(x_min=100, y_min=20, y_max=60)),
                         pass_end_location > in_range(x_min=100, y_min=20, y_max=60),]),
    CommentaryClip(153, [event_type_is('Pass'),
                         comment('Is this the vital opening?'),
                         successful_pass,
                         through_ball]),
    CommentaryClip(154, [event_type_is('Dribble'),
                         comment('He has managed to avoid the tackle'),
                         lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(157, [event_type_is('Dribble'),
                         comment('Skips past the defender...'),
                         location > in_offensive_third,
                         lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(158, [event_type_is('Dribble'),
                         comment('He has rounded the defence'),
                         location > in_range(x_min=100),
                         lambda x: x.dribble.outcome.name == 'Complete']),
    CommentaryClip(160, [event_type_is('Pass'),
                         comment('Just the goalkeeper to beat, now'),
                         successful_pass,
                         through_ball]),
    CommentaryClip(161, [todo('One on one with the goalkeeper')]),
    CommentaryClip(162, [todo('He cannot miss from here')]),
    CommentaryClip(163, [todo('He just needs to steady himself')]),

    CommentaryClip(164, [todo('There is the equaliser they needed - can we even do scorelines??')]),

    CommentaryClip(175, [event_type_is('Shot'),
                         comment('Goal!'),
                         lambda x: x.shot.outcome.name == 'Goal']),

    CommentaryClip(194, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.02]),
    CommentaryClip(197, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.02]),
    CommentaryClip(199, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.statsbomb_xg <= 0.20,
                         xg2_at_least(0.60)]),
    CommentaryClip(202, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         xg2_at_least(0.50)]),
    CommentaryClip(203, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         xg2_at_least(0.50)]),
    CommentaryClip(204, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.body_part.name == 'Head',
                         xg2_at_least(0.30)]),
    CommentaryClip(206, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         xg2_at_least(0.50)]),
    CommentaryClip(207, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.body_part.name == 'Head',
                         xg2_at_least(0.10)]),
    CommentaryClip(209, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.body_part.name == 'Head',
                         xg2_at_least(0.30)]),
    CommentaryClip(213, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',]),

    CommentaryClip(215, [todo('What skill')]),
    CommentaryClip(217, [todo('He made it look so easy')]),
    CommentaryClip(217, [todo('Superb first touch')]),

    CommentaryClip(221, [event_type_is('Shot'),
                         comment('It\'s a goal!'),
                         lambda x: x.shot.outcome.name == 'Goal',]),
    CommentaryClip(222, [event_type_is('Shot'),
                         comment('Incredible timing!'),
                         lambda x: x.shot.type.name == 'Goal',
                         lambda x: x.shot.technique.name == 'Volley']),
    CommentaryClip(226, [event_type_is('Shot'),
                         comment('A textbook set piece!'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.type.name == 'Free Kick']),
    CommentaryClip(228, [event_type_is('Shot'),
                         comment('They must have practiced that one before'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.type.name == 'Free Kick']),
    CommentaryClip(229, [event_type_is('Shot'),
                         comment('In the net!'),
                         lambda x: x.shot.outcome.name == 'Goal']),
    CommentaryClip(230, [event_type_is('Shot'),
                         comment('It was no accident!'),
                         lambda x: x.shot.outcome.name == 'Goal']),
    CommentaryClip(234, [event_type_is('Shot'),
                         comment('It\'s there!'),
                         lambda x: x.shot.outcome.name == 'Goal']),
    CommentaryClip(235, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.one_on_one]),
    CommentaryClip(238, [event_type_is('Shot'),
                         comment('He left the goalkeeper with no chance'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         xg2_at_least(0.30)]),
    CommentaryClip(241, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.one_on_one]),
    CommentaryClip(243, [event_type_is('Shot'),
                         comment('Great penalty!'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         lambda x: x.shot.type.name == 'Penalty']),
    CommentaryClip(255, [event_type_is('Shot'),
                         comment('Are we about to see the floodgates open?'),
                         lambda x: x.shot.outcome.name == 'Goal']),

    CommentaryClip(299, [event_type_is('Shot'),
                         comment('And that is like a long cool drink for a very thirsty man!!'),
                         lambda x: x.shot.outcome.name == 'Goal',
                         with_weight(0.1)]),

    CommentaryClip(314, [todo('Own goal')]),
    CommentaryClip(316, [todo('Own goal')]),
    CommentaryClip(317, [todo('Own goal')]),
    CommentaryClip(320, [todo('Own goal')]),

    CommentaryClip(333, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(334, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(336, [event_type_is('Shot'),
                         lambda x: x.shot.technique.name == 'Volley',
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(338, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(341, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(345, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Wayward']),
    CommentaryClip(349, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(353, [event_type_is('Shot'),
                         location > in_range(x_max=95),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(355, [todo('Going wide of the post')]),
    CommentaryClip(358, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(362, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(366, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(367, [event_type_is('Shot'),
                         lambda x: x.shot.statsbomb_xg > 0.15,
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(370, [todo('He has pulled it well wide')]),
    CommentaryClip(375, [todo('Over the crossbar')]),
    CommentaryClip(378, [todo('He had skied it')]),
    CommentaryClip(380, [todo('Did not dip early enough to trouble the goalkeeper')]),
    CommentaryClip(383, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Off T']),
    CommentaryClip(384, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Saved']),
    CommentaryClip(387, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Saved']),
    CommentaryClip(389, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Saved',
                         xg2_at_least(0.15)]),
    CommentaryClip(391, [todo('Plucks it out of the air safely')]),
    CommentaryClip(398, [event_type_is('Shot'),
                         lambda x: x.shot.outcome.name == 'Saved',
                         xg2_at_least(0.15)]),


    # Throw ins
    # TODO: check that it goes out off the *side* of the pitch
    CommentaryClip(401, [event_type_is('Pass'), pass_outcome('Out')]),
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

    CommentaryClip(431, [todo('They will probably have a shot from here')]),
    CommentaryClip(432, [todo('Seen them go in from here')]),

    # Great expectancy!
    CommentaryClip(434, [event_type_is('Ball Receipt*'),
                         location > in_range(x_min=100, y_min=30, y_max=50)]),

    CommentaryClip(435, [event_type_is('Foul Committed')]),
    CommentaryClip(436, [todo('Not surprised that he is injured')]),
    CommentaryClip(439, [todo('That looked painful')]),
    CommentaryClip(440, [todo('Hope it is nothing serious')]),
    CommentaryClip(441, [todo('Cycnical challenge')]),
    CommentaryClip(442, [todo('He does look in pain')]),

    CommentaryClip(446, [todo('Offside')]),
    CommentaryClip(447, [todo('Offside')]),
    CommentaryClip(448, [todo('Offside')]),
    CommentaryClip(449, [todo('What a shame')]),
    CommentaryClip(450, [todo('Would have been a great chance')]),
    CommentaryClip(453, [todo('Yellow card')]),
    CommentaryClip(455, [todo('Crazy challenge. Yellow card')]),
    CommentaryClip(457, [todo('Referee issues a caution')]),

    # I think from this point the clips aren't properly spliced
)
