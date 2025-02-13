#
# Copyright 2009-2012 Alex Fraser <alex@phatcore.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging

import bge
import mathutils

import bat.bats
import bat.bmath
import bat.event
import bat.sound
import bat.anim
import bat.render
import bat.store

import Scripts.story
import Scripts.shaders
import Scripts.director
import Scripts.story_ant

log = logging.getLogger(__name__)

class LevelBeehive(Scripts.story.GameLevel):
    def __init__(self, oldOwner):
        Scripts.story.GameLevel.__init__(self, oldOwner)
        Scripts.shaders.ShaderCtrl().set_mist_colour(
                mathutils.Vector((0.0, 0.0, 0.0)))
        Scripts.shaders.ShaderCtrl().set_mist_depth(100)


def _music_start(owner):
    bat.sound.Jukebox().play_files('dungeon', owner, 1,
            '//Sound/Music/09-TheDungeon_loop.ogg',
            introfile='//Sound/Music/09-TheDungeon_intro.ogg',
            volume=0.4, fade_in_rate=1, fade_out_rate=0.002)

def _music_stop():
    bat.sound.Jukebox().stop('dungeon')

def music(c):
    s = c.sensors[0]
    if not s.triggered:
        return
    if s.positive:
        _music_start(c.owner)
    else:
        _music_stop()

def music_start(c):
    s = c.sensors[0]
    if s.triggered and s.positive:
        _music_start(c.owner)

def music_stop(c):
    s = c.sensors[0]
    if s.triggered and s.positive:
        _music_stop()


#class AntControl(bat.bats.BX_GameObject, bge.types.BL_ArmatureObject):
#    _prefix = 'AC_'
#    def __init__(self, old_owner):
#        pass
#
#    @bat.types.expose
#    @bat.utils.controller_cls

def create_ant(c):
    ''''Create and position ant. The Ant class takes care of the rest.'''
    spawn_point = c.owner
    ant = Scripts.story_ant.factory()
    bat.bmath.copy_transform(spawn_point, ant)


def approach_window(c):
    '''Triggers the animation of the ant grabbing the bucket.'''
    mainc = Scripts.director.Director().mainCharacter
    if mainc is None:
        return
    dist = (mainc.worldPosition - c.owner.worldPosition).magnitude
    if dist < 9.5:
        bat.event.Event('ApproachWindow').send()


def init_conveyor(c):
    o = c.owner
    cpath = o.children['ConveyorBelt']
    bat.anim.play_children_with_offset(cpath.children, 'ConveyorBelt_SegAction',
        1, 601)

    flower_box = o.childrenRecursive['FlowerBox']
    flower_box.playAction('FlowerBoxAction', 1, 61,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

    roller_holder = o.childrenRecursive['RollerHolder.1']
    roller_holder.playAction('RollerHolder.1Action', 1, 91,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

    peg1 = o.children['ConveyorPeg.1']
    peg1.playAction('ConveryorPegAction', 1, 61,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)
    peg2 = o.children['ConveyorPeg.2']
    peg2.playAction('ConveryorPegAction', 1, 61,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

    crusher1 = o.children['ConveyorCrusher_root.1']
    crusher1loc = crusher1.children[0]
    crusher1loc.playAction('ConveyorCrusher_Loc.1Action', 1, 601,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)
    crusher1rot = crusher1loc.children[0]
    crusher1rot.playAction('ConveyorCrusher_RotAction', 1, 91,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

    crusher2 = o.children['ConveyorCrusher_root.2']
    crusher2loc = crusher2.children[0]
    crusher2loc.playAction('ConveyorCrusher_Loc.2Action', 1, 601,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)
    crusher2rot = crusher2loc.children[0]
    crusher2rot.playAction('ConveyorCrusher_RotAction', 1, 91,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

    sce = bge.logic.getCurrentScene()
    crusher3rot = sce.objects['FlowerCrusher']
    crusher3rot.playAction('ConveyorCrusher_RotAction', 1, 91,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)
    crusher4rot = sce.objects['FlowerCrusher.001']
    crusher4rot.playAction('ConveyorCrusher_RotAction', 1, 91,
            play_mode=bge.logic.KX_ACTION_MODE_LOOP)

def spawn_flower_head(c):
    if not c.sensors[0].positive:
        return
    sce = bge.logic.getCurrentScene()
    rnd = mathutils.noise.random()
    templates = ('FlowerDaisyHead', 'FlowerBellHead', 'FlowerPinkHead')
    i = min(int(len(templates) * rnd), len(templates))
    template = templates[i]
    instance = sce.addObject(template, c.owner, 1000)
    instance.worldLinearVelocity.z -= 10
    orn = mathutils.Vector((0, 0, 1.0)) + mathutils.noise.random_unit_vector()
    orn.normalize()
    instance.alignAxisToVect(orn, 2)

def flower_crush(c):
    if not c.sensors[0].positive:
        return
    target = c.sensors[0].hitObject['CrushAmount']
    c.owner.localScale.z = bat.bmath.lerp(c.owner.localScale.z, target, 0.1)


def rubber_band_sound(c):
    s = c.sensors[0]
    if s.positive and s.triggered:
        sample = bat.sound.Sample(
                '//Sound/cc-by/RubberBandRub1.ogg',
                '//Sound/cc-by/RubberBandRub2.ogg',
                '//Sound/cc-by/RubberBandRub3.ogg')
        sample.volume = 0.7
        sample.add_effect(bat.sound.Localise(c.owner, distmax=70))
        sample.pitchmin = 0.9
        sample.pitchmax = 1.0
        sample.play()
    else:
        # No need to stop because sounds don't loop.
        pass

def draining_sound(c):
    s = c.sensors[0]
    if s.positive and s.triggered:
        sample = bat.sound.Sample('//Sound/cc-by/Draining.ogg')
        sample.volume = 0.4
        sample.add_effect(bat.sound.Localise(c.owner, distmax=70))
        sample.loop = True
        c.owner['drain_sound'] = sample
        sample.play()
    elif not s.positive and s.triggered:
        sample = c.owner['drain_sound']
        sample.stop()

def machine_sound(c):
    s = c.sensors[0]
    if s.positive and s.triggered:
        sample = bat.sound.Sample('//Sound/Machine1.ogg')
        sample.volume = 0.7
        sample.add_effect(bat.sound.Localise(c.owner, distmax=50))
        sample.loop = True
        c.owner['machine_sound'] = sample
        sample.play()
    elif not s.positive and s.triggered:
        sample = c.owner['machine_sound']
        sample.stop()


def init_lower_buckets(c):
    log.info('Starting lower buckets')
    o = c.owner
    bat.anim.play_children_with_offset(o.children, 'BucketsLower', 1, 400)

class BucketControlUpper(bat.bats.BX_GameObject, bge.types.KX_GameObject):
    '''
    Second set of buckets is a little more complicated because they need to
    interact with the Ant.
    '''

    log = logging.getLogger(__name__ + '.BucketControlUpper')

    def __init__(self, old_owner):
        self.start()
        bat.event.EventBus().add_listener(self)

    def on_event(self, evt):
        if evt.message == 'ParkBuckets':
            self.park()
        elif evt.message == 'StartBuckets':
            self.start()

    def start(self):
        BucketControlUpper.log.info('Starting upper buckets')
        bat.anim.play_children_with_offset(self.children, 'BucketsUpper', 1, 1334)
        if bat.store.get('/game/level/AntGrabbed', defaultValue=False):
            BucketControlUpper.log.info('Deleting thimble bucket')
            # Hackish: This happens to work because it only happens once. If the
            # buckets were re-started after this, the spacing would be wrong.
            # But that's not such a big deal, anyway.
            self.childrenRecursive['ThimbleBucket'].endObject()

    def park(self):
        BucketControlUpper.log.info('Parking upper buckets')
        for child in self.children:
            child.playAction('BucketsUpper', 1, 1, 0)


class Bucket(bat.bats.BX_GameObject, bge.types.KX_GameObject):
    '''An animated conveyor object.'''

    log = logging.getLogger(__name__ + '.Bucket')

    WATERBALL_VELOCITY = [0.0, 0.0, 20.0]

    def __init__(self, old_owner):
        self.water = self.find_descendant([('Type', 'BucketWater')])
        self.occupied = False
        if 'colour' in self:
            col= bat.render.parse_colour(self['colour'])
            self.color = col

    def set_location(self, location):
        '''
        Called by sensors along the animated path of the bucket. Allows the
        bucket to perform actions at certain locations. See bucket_location().
        '''
        if location == 'TIPPING':
            self.tip()
        elif location == 'ASCENDING':
            self.ascend()

    def tip(self):
        Bucket.log.debug("%s %s", self.name, "TIPPING")
        water = self.water
        water.visible = False
        waterBall = self.scene.addObject('WaterBall', water)
        waterBall.setLinearVelocity(water.getAxisVect(Bucket.WATERBALL_VELOCITY))

    def ascend(self):
        Bucket.log.debug("%s %s", self.name, "ASCENDING")
        water = self.water
        water.visible = True

    def set_occupied(self, occupied):
        if self.occupied == occupied:
            return
        Bucket.log.debug("%s %s = %s", self.name, "OCCUPIED", occupied)
        self.occupied = occupied


class BucketLower(Bucket):
    '''Specialised bucket that controls the camera while the player is inside.'''
    def __init__(self, old_owner):
        Bucket.__init__(self, old_owner)
        self.at_top = False
        self.current_camera = None

    def set_location(self, location):
        if location == 'TOP':
            self.approach_top()
        elif location == 'BOTTOM':
            self.approach_bottom()
        else:
            Bucket.set_location(self, location)

    def approach_top(self):
        if self.at_top:
            return
        Bucket.log.debug("%s %s", self.name, "TOP")
        self.at_top = True
        self.update_camera()

    def approach_bottom(self):
        if not self.at_top:
            return
        Bucket.log.debug("%s %s", self.name, "BOTTOM")
        self.at_top = False
        self.update_camera()

    def set_occupied(self, occupied):
        if self.occupied == occupied:
            return
        Bucket.log.debug("%s %s = %s", self.name, "OCCUPIED", occupied)
        self.occupied = occupied
        if occupied:
            bat.event.Event('GameModeChanged', 'Cutscene').send()
        else:
            bat.event.Event('GameModeChanged', 'Playing').send()
        self.update_camera()

    def update_camera(self):
        cam = None
        if self.occupied:
            if not self.at_top:
                cam = 'BucketBottomCam'
            else:
                cam = 'BucketTopCam'

        if (cam is None) and (self.current_camera is not None):
            # Player is being ejected; update camera position to prevent
            # jolting.
            Bucket.log.info("Relocating player camera")
            camob = self.scene.objects[self.current_camera]
            pos = camob.worldPosition
            orn = camob.worldOrientation
            bat.event.Event('RelocatePlayerCamera', (pos, orn)).send()

        if cam is self.current_camera:
            return

        Bucket.log.info("Setting camera to %s", cam)

        # Add new camera first for better cutting
        if cam is not None:
            bat.event.Event('AddCameraGoal', cam).send()
        if self.current_camera is not None:
            bat.event.Event('RemoveCameraGoal', self.current_camera).send()

        self.current_camera = cam

def bucket_water_touched(c):
    # Called by a sensor inside the bucket, which is a child of the bucket.
    s = c.sensors[0]
    is_occupied = Scripts.director.Director().mainCharacter in s.hitObjectList
    c.owner.parent.set_occupied(is_occupied)

def bucket_location(c):
    # Called by sensors around the bucket track, which are independent.
    s = c.sensors[0]
    if not s.positive:
        return
    for ob in s.hitObjectList:
        ob.set_location(c.owner['location'])

class DefenceRoom(bat.bats.BX_GameObject, bge.types.KX_GameObject):
    _prefix = 'DR_'

    S_INIT = 1
    S_TIMER = 2

    TIME = 10

    def __init__(self, old_owner):
        self.is_open = False
        self.time_remaining = 0
        self.total_time = DefenceRoom.TIME * bge.logic.getLogicTicRate()
        bat.event.EventBus().add_listener(self)

    def on_event(self, evt):
        if evt.message == 'HitButton':
            self.hit_button()
        elif evt.message == 'LeftButton':
            self.left_button()
        elif evt.message == 'OpenTopDoor':
            self.open_door()
        elif evt.message == 'CloseTopDoor':
            self.close_door()
        elif evt.message == 'HoldTopDoor':
            self.cancel_timer()

    def hit_button(self):
        player = Scripts.director.Director().mainCharacter
        if player is None:
            return
        speed = player.lastLinV.magnitude
        if speed > 30.0:
            self.open_door()
            self.time_remaining = self.total_time
            bat.event.Event('TimeSet', 1).send()

    def left_button(self):
        if self.is_open:
            self.add_state(DefenceRoom.S_TIMER)

    @bat.bats.expose
    def update(self):
        self.time_remaining -= 1
        if self.time_remaining <= 0:
            self.rem_state(DefenceRoom.S_TIMER)
            bat.event.Event('TimeSet', 0).send()
            self.close_door()
        else:
            tfrac = self.time_remaining / self.total_time
            bat.event.Event('TimeSet', tfrac).send()

    def cancel_timer(self):
        self.time_remaining = 0
        bat.event.Event('TimeSet', 0).send()
        self.rem_state(DefenceRoom.S_TIMER)

    def open_door(self):
        if self.is_open:
            return
        for bollard_base in self.children['Bollards'].children:
            bollard = bollard_base.children[0]
            bollard.playAction('Bollard', 1, 23)
        for door_base in self.children['TopDoor'].children:
            door = door_base.children[0]
            door.playAction('DefenceDoor', 1, 23)
        self.is_open = True

    def close_door(self):
        if not self.is_open:
            return
        for bollard_base in self.children['Bollards'].children:
            bollard = bollard_base.children[0]
            bollard.playAction('Bollard', 40, 62)
        for door_base in self.children['TopDoor'].children:
            door = door_base.children[0]
            door.playAction('DefenceDoor', 40, 62)
        self.is_open = False


def button_sense(c):
    # Can't use plain near sensor here, in case player leaves shell while
    # on button (very likely).
    mainc = Scripts.director.Director().mainCharacter
    if mainc is None:
        return
    o = c.owner
    dist = (mainc.worldPosition - o.worldPosition).magnitude
    if (not o['positive']) and dist < 3.5:
        bat.event.Event('HitButton').send()
        o['positive'] = True
    elif o['positive'] and dist > 4.0:
        bat.event.Event('LeftButton').send()
        o['positive'] = False