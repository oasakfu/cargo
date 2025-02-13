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

import math
import re

import bge
import mathutils

import bat.bats
import bat.containers
import bat.event
import bat.sound
import bat.utils
import bat.bmath
import bat.impulse

class UiController(bat.impulse.Handler, bat.bats.BX_GameObject,
        bge.types.KX_GameObject):

    '''Manages UI elements: focus and click events.'''

    _prefix = 'UC_'

    current = bat.containers.weakprop("current")
    downCurrent = bat.containers.weakprop("downCurrent")

    DIRECTION_TOLERANCE = 0.1
    #SOUND_DELAY_TICS = 5
    SOUND_DELAY_TICS = 0

    def __init__(self, old_owner):
        self.screen_stack = []
        bat.impulse.Input().add_handler(self, 'MAINMENU')
        bat.impulse.allow_mouse_capture = False

        # Don't play the first focus sound.
        self.sound_delay = UiController.SOUND_DELAY_TICS
        self.focus_sound = bat.sound.Sample("//Sound/cc-by/BtnFocus.ogg")
        self.focus_sound.volume = 0.2
        self.click_sound = bat.sound.Sample("//Sound/cc-by/BtnClick.ogg")
        self.click_sound.volume = 0.2

        bat.event.EventBus().add_listener(self)
        bat.event.EventBus().replay_last('setScreen', self)
        #bat.event.EventBus().replay_last('pushScreen', self)
        #bat.event.EventBus().replay_last('popScreen', self)

    def on_event(self, evt):
        if evt.message == 'setScreen':
            self.screen_stack = [evt.body]
            self.update_screen()
        elif evt.message == 'switchScreen':
            # Swap the requested screen for the one on top of the stack.
            if len(self.screen_stack) == 0:
                self.screen_stack.append(evt.body)
            else:
                self.screen_stack[-1] = evt.body
                self.update_screen()
        elif evt.message == 'pushScreen':
            if evt.body in self.screen_stack:
                self.screen_stack.remove(evt.body)
            self.screen_stack.append(evt.body)
            self.update_screen()
        elif evt.message == 'popScreen':
            if len(self.screen_stack) == 0 or len(self.screen_stack) == 1 and self.screen_stack[0] == 'LoadingScreen':
                bat.event.Event('confirmation', 'Do you really want to quit?::quit::').send(1)
            else:
                self.screen_stack.pop()
                self.update_screen()

    @bat.bats.expose
    def pulse(self):
        if self.sound_delay > 0:
            self.sound_delay -= 1

    def update_screen(self):
        if len(self.screen_stack) > 0:
            screen_name = self.screen_stack[-1]
        else:
            screen_name = 'LoadingScreen'
        bat.event.Event('showScreen', screen_name).send()

        # Previous widget is probably hidden now; switch to default for this
        # screen.
        widget = self.get_default_widget(screen_name)

        if widget is not None:
            self.focus(widget)

    def get_default_widget(self, screen_name):
        return None

    @bat.bats.expose
    @bat.utils.controller_cls
    def mouseMove(self, c):
        if not c.sensors['sMouseMove'].positive:
            return
        bge.logic.mouse.visible = True
        mOver = c.sensors['sMouseOver']
        mOver.usePulseFocus = True
        self.mouseOver(mOver)

    @bat.bats.expose
    def mouseOver(self, mOver):
        newFocus = mOver.hitObject

        # Bubble up to ancestor if need be
        while newFocus is not None:
            if 'Widget' in newFocus:
                break
            newFocus = newFocus.parent

        self.focus(newFocus)

    def focus(self, widget):
        if widget is self.current:
            return

        self.current = widget
        bat.event.WeakEvent("FocusChanged", widget).send()
        if widget is not None and self.sound_delay <= 0:
            self.focus_sound.play()
            self.sound_delay = UiController.SOUND_DELAY_TICS

    def press(self):
        '''Send a mouse down event to the widget under the cursor.'''
        if self.current:
            self.current.down()
            self.downCurrent = self.current

    def release(self):
        '''Send a mouse up event to the widget under the cursor. If that widget
        also received the last mouse down event, it will be sent a click event
        in addition to (after) the up event.'''
        if self.downCurrent:
            self.downCurrent.up()
            if self.current == self.downCurrent:
                # Always play click sound, but then disallow other sounds like
                # focus. Note that this must happen before click() is called,
                # or the focus sound will play anyway.
                self.click_sound.play()
                self.sound_delay = UiController.SOUND_DELAY_TICS

                self.downCurrent.click()
        self.downCurrent = None

    def can_handle_input(self, state):
        return state.name in ('1', '2', 'Movement', 'Start', 'CameraMovement')

    def handle_input(self, state):
        if state.name == '1':
            self.handle_bt_1(state)
        elif state.name == '2':
            self.handle_bt_2(state)
        elif state.name == 'Start':
            self.handle_bt_start(state)
        elif state.name in {'Movement', 'CameraMovement'}:
            self.handle_movement(state)

    def handle_bt_1(self, state):
        '''Activate current widget (keyboard/joypad).'''
        if state.triggered:
            if state.positive:
                self.press()
            else:
                self.release()

    def handle_bt_2(self, state):
        '''Escape from current screen (keyboard/joypad).'''
        if state.activated:
            bat.event.Event('popScreen').send()

    def handle_bt_start(self, state):
        '''Escape from current screen (keyboard/joypad).'''
        if state.activated:
            bat.event.Event('popScreen').send()

    def handle_movement(self, state):
        '''Switch to neighbouring widgets (keyboard/joypad).'''
        if not state.triggered_repeat or state.bias.magnitude < 0.1:
            return

        bge.logic.mouse.visible = False

        widget = self.find_next_widget(state.bias)
        if widget is not None:
            self.focus(widget)

    def find_next_widget(self, direction):
        cam = self.scene.active_camera
        if self.current is not None and self.current.is_visible:
            loc = self.current.worldPosition
        else:
            loc = mathutils.Vector((0.0, 0.0, 0.0))
        world_direction = bat.bmath.to_world_vec(cam, direction.resized(3))
        world_direction.normalize()

        # Iterate over widgets, assigning each one a score - based on the
        # direction of the movement and the location of the current widget.
        best_widget = None
        best_score = 0.0
        for ob in self.scene.objects:
            if not 'Widget' in ob or not ob.is_visible or not ob.sensitive:
                continue
            ob_dir = ob.worldPosition - loc
            dist = ob_dir.magnitude
            if dist == 0.0:
                continue
            score_dist = 1.0 / dist
            score_dist = math.pow(score_dist, 2)

            ob_dir.normalize()
            score_dir = ob_dir.dot(world_direction)
            if score_dir < UiController.DIRECTION_TOLERANCE:
                continue
            score_dir = math.pow(score_dir, 2)

            score = score_dir * score_dist
            if score > best_score:
                best_score = score
                best_widget = ob

        return best_widget


class Widget(bat.bats.BX_GameObject, bge.types.KX_GameObject):
    '''An interactive UIObject. Has various states (e.g. focused, up, down) to
    facilitate interaction. Some of the states map to a frame to allow a
    visual progression.'''

    S_FOCUS = 2
    S_DEFOCUS = 3
    S_DOWN = 4
    S_UP = 5
    S_HIDING = 16
    S_VISIBLE = 17

    FRAME_RATE = 25.0 / bge.logic.getLogicTicRate()

    # These should be matched to the FCurve or action of the object associated
    # with this widget. The animation is not actually driven by this script; it
    # just sets the object's 'frame' property, which should be observed by an
    # actuator.
    HIDDEN_FRAME = 1.0
    IDLE_FRAME = 5.0
    FOCUS_FRAME = 9.0
    ACTIVE_FRAME = 12.0

    def __init__(self, old_owner):
        if 'sensitive' in self:
            self.sensitive = self['sensitive']
        else:
            self.sensitive = True
        self['Widget'] = True
        self.original_position = self.localPosition.copy()
        self.should_be_visible = False
        self.is_visible = False
        if 'can_display' in self:
            self.can_display = self['can_display']
        else:
            self.can_display = True
        self.hide()

        bat.event.EventBus().add_listener(self)
        bat.event.EventBus().replay_last(self, 'showScreen')

    def enter(self):
        if not self.sensitive:
            return
        if self.has_state(Widget.S_FOCUS):
            return
        self.add_state(Widget.S_FOCUS)
        self.rem_state(Widget.S_DEFOCUS)
        self.updateTargetFrame()

    def leave(self):
        if not self.has_state(Widget.S_FOCUS):
            return
        self.add_state(Widget.S_DEFOCUS)
        self.rem_state(Widget.S_FOCUS)
        self.updateTargetFrame()

    def down(self):
        if not self.sensitive:
            return
        self.add_state(Widget.S_DOWN)
        self.rem_state(Widget.S_UP)
        self.updateTargetFrame()

    def up(self):
        self.add_state(Widget.S_UP)
        self.rem_state(Widget.S_DOWN)
        self.updateTargetFrame()

    def click(self):
        if not self.sensitive:
            return
        if 'onClickMsg' in self:
            msg = self['onClickMsg']
            body = ''
            if 'onClickBody' in self:
                body = self['onClickBody']
            evt = bat.event.Event(msg, body)
            bat.event.EventBus().notify(evt)

    def on_event(self, evt):
        if evt.message == 'showScreen':
            if 'screenName' in self:
                if re.match(self['screenName'], evt.body) is not None:
                    self.show()
                else:
                    self.hide()

        elif evt.message == 'FocusChanged':
            if evt.body is not self:
                self.leave()
            else:
                self.enter()

    def hide(self):
        self.should_be_visible = False
        self.is_visible = False
        self.setVisible(False, False)
        self.rem_state(Widget.S_DOWN)
        self.rem_state(Widget.S_FOCUS)
        self.add_state(Widget.S_HIDING)
        self.rem_state(Widget.S_VISIBLE)
        self.updateTargetFrame()

    def show(self):
        self.should_be_visible = True
        if not self.can_display:
            return
        self.is_visible = True
        self.setVisible(True, False)
        self.rem_state(Widget.S_HIDING)
        self.add_state(Widget.S_VISIBLE)
        self.updateTargetFrame()
        self.updateVisibility(True)

    def get_anim_range(self, target_ob=None):
        if target_ob is None:
            target_ob = self
        targetFrame = Widget.IDLE_FRAME
        if not self.is_visible:
            targetFrame = Widget.HIDDEN_FRAME
        elif self.has_state(Widget.S_FOCUS):
            if self.has_state(Widget.S_DOWN):
                targetFrame = Widget.ACTIVE_FRAME
            else:
                targetFrame = Widget.FOCUS_FRAME
        else:
            targetFrame = Widget.IDLE_FRAME

        cfra = max(target_ob.getActionFrame(), 1.0)
        return cfra, targetFrame

    def updateTargetFrame(self, target_ob=None):
        if target_ob is None:
            target_ob = self
        # Progress animation from current frame to target frame.
        start, end = self.get_anim_range(target_ob)
        target_ob.playAction("Widget", start, end)

    @bat.bats.expose
    def update(self):
        '''Checks whether a widget is fully hidden yet.'''
        if self.getActionFrame() <= 1.0:
            self.updateVisibility(False)
            self.rem_state(Widget.S_HIDING)

    def updateVisibility(self, visible):
        for descendant in self.childrenRecursive:
            if 'alwayshide' in descendant:
                continue
            descendant.visible = visible
        if visible:
            self.localPosition = self.original_position
        else:
            self.localPosition = self.original_position
            self.localPosition.y += 100.0

    def setSensitive(self, sensitive):
        oldv = self.sensitive
        self.sensitive = sensitive
        if oldv != sensitive:
            evt = bat.event.Event('sensitivityChanged', self.sensitive)
            bat.event.EventBus().notify(evt)

    @property
    def can_display(self):
        return self._can_display

    @can_display.setter
    def can_display(self, value):
        self._can_display = value
        if self.should_be_visible and not self.is_visible:
            self.show()
        elif not self.should_be_visible and self.is_visible:
            self.hide()


class Button(Widget):
    def __init__(self, old_owner):
        # A Widget has everything needed for a simple button.
        Widget.__init__(self, old_owner)

