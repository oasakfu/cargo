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

import bge

import bat.bats
import bat.sound
import bat.event
import bat.utils
import bat.bmath
import bat.story

import Scripts.story

def factory(sce):
    if not "Spider" in sce.objectsInactive:
        try:
            bge.logic.LibLoad('//Spider_loader.blend', 'Scene', load_actions=True)
        except ValueError as e:
            print('Warning: could not load spider:', e)

    return bat.bats.add_and_mutate_object(sce, "Spider", "Spider")

class SpiderIsle(bat.bats.BX_GameObject, bge.types.KX_GameObject):

    _prefix = "SI_"

    def __init__(self, old_owner):
        self.catapult_primed = False
        bat.event.EventBus().add_listener(self)

    def on_event(self, evt):
        if evt.message == 'ShellDropped':
            self.play_flying_cutscene(evt.body)

    def play_music(self):
        bat.sound.Jukebox().play_files('spider', self, 1,
                '//Sound/Music/07-TheSpider_loop.ogg',
                introfile='//Sound/Music/07-TheSpider_intro.ogg',
                fade_in_rate=1)

    def stop_music(self):
        bat.sound.Jukebox().stop('spider')

    @bat.bats.expose
    @bat.utils.controller_cls
    def approach_isle(self, c):
        if c.sensors[0].positive:
            bat.store.put('/game/level/spawnPoint', 'SI_StartSpawnPoint')
            self.play_music()

    @bat.bats.expose
    @bat.utils.controller_cls
    def approach_centre(self, c):
        if c.sensors[0].positive:
            bat.store.put('/game/level/spawnPoint', 'SI_WebSpawnPoint')
            if 'Spider' in self.scene.objects:
                return
            spider = factory(self.scene)
            spawn_point = self.scene.objects['Spider_SpawnPoint']
            bat.bmath.copy_transform(spawn_point, spider)
            self.play_music()
        else:
            if 'Spider' not in self.scene.objects:
                return
            spider = self.scene.objects['Spider']
            spider.endObject()

    @bat.bats.expose
    @bat.utils.controller_cls
    def approach_web(self, c):
        for s in c.sensors:
            if not s.positive:
                continue
            player = s.hitObject
            if not player.is_in_shell:
                bat.event.Event('ApproachWeb').send()
            return
        # else
        bat.event.Event('LeaveWeb').send()

    @bat.bats.expose
    @bat.utils.controller_cls
    def in_bounds(self, c):
        if not c.sensors[0].positive:
            self.stop_music()

    @bat.bats.expose
    @bat.utils.controller_cls
    def catapult_end_touched(self, c):
        self.catapult_primed = c.sensors[0].positive
        if self.catapult_primed:
            print("side cam")
            bat.event.Event("AddCameraGoal", "FC_SideCamera_Preview").send()
        else:
            bat.event.Event("RemoveCameraGoal", "FC_SideCamera_Preview").send()

    def play_flying_cutscene(self, shell):
        if not self.catapult_primed:
            return
        if shell is None or shell.name != "Nut":
            return

        snail = Scripts.director.Director().mainCharacter
        snail_up = snail.getAxisVect(bat.bmath.ZAXIS)
        if snail_up.dot(bat.bmath.ZAXIS) < 0.0:
            # Snail is upside down, therefore on wrong side of catapult
            return

        spawn_point = self.scene.objects["FC_SpawnPoint"]
        bat.bats.add_and_mutate_object(self.scene, "FlyingCutscene", spawn_point)


class Spider(bat.story.Chapter, bat.bats.BX_GameObject, bge.types.BL_ArmatureObject):
    L_ANIM = 0
    L_IDLE = 1

    def __init__(self, old_owner):
        bat.story.Chapter.__init__(self, old_owner)
        self.anim_welcome = bat.story.AnimBuilder('Spider_conv', layer=Spider.L_ANIM)
        self.anim_nice = bat.story.AnimBuilder('Spider_conv_nice', layer=Spider.L_ANIM)
        self.anim_rude = bat.story.AnimBuilder('Spider_conv_rude', layer=Spider.L_ANIM)
        self.anim_get = bat.story.AnimBuilder('Spider_conv_get', layer=Spider.L_ANIM)
        self.create_state_graph()

    def create_state_graph(self):
        sinit = self.rootState.create_successor("Init")
        self.anim_welcome.play(sinit, 1, 1)
        sinit.add_action(bat.story.ActAction('Spider_idle', 1, 60, Spider.L_IDLE,
                play_mode=bge.logic.KX_ACTION_MODE_LOOP))

        # This graph plays the first time you meet the spider.
        swelcome_start, swelcome_end = self.create_welcome_graph()
        swelcome_start.add_predecessor(sinit)

        # This one plays when you pick up the wheel.
        sget_start, sget_end = self.create_wheel_get_graph()
        sget_start.add_predecessor(sinit)

        # This one plays if you approach the spider again after getting the
        # wheel.
        safter_start, safter_end = self.create_after_wheel_graph()
        safter_start.add_predecessor(sinit)

        sinit.add_predecessor(swelcome_end)
        sinit.add_predecessor(sget_end)
        sinit.add_predecessor(safter_end)

    def create_welcome_graph(self):
        sstart = (bat.story.State("Welcome")
            (bat.story.CNot(Scripts.story.CondHasShell("Wheel")))
            (bat.story.CondEvent("ApproachWeb", self))
        )

        s = (sstart.create_successor()
            (Scripts.story.ActSuspendInput())
            (Scripts.story.ActSetFocalPoint('Spider'))
            (Scripts.story.ActSetCamera("SpiderCam"))
        )

        # Catch-many state for when the user cancels a dialogue. Should only be
        # allowed if the conversation has been played once already.
        scancel = (bat.story.State("Cancel")
            (bat.story.CondEvent('DialogueCancelled', self))
            (bat.story.CondStore('/game/level/spiderWelcome1', True, default=False))
        )

        s = (s.create_successor()
            (Scripts.story.ActSetCamera("SpiderCam_CU"))
            ("ShowDialogue", "Who goes there?")
            (bat.story.ActSound('//Sound/sdr.bossy2.ogg', vol=3))
        )
        self.anim_welcome.play(s, 1, 20)
        scancel.add_predecessor(s)

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "Ah, where are my manners? Welcome, my dear! Forgive me; I don't get many visitors.")
            (bat.story.ActSound('//Sound/sdr.interest4.ogg', vol=3))
            (bat.story.State()
                (bat.story.CondActionGE(Spider.L_ANIM, 36, tap=True))
                (Scripts.story.ActRemoveCamera("SpiderCam_CU"))
                (Scripts.story.ActSetCamera("SpiderCam_Side"))
            )
        )
        self.anim_welcome.play(s, 30, 45)
        scancel.add_predecessor(s)

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            (Scripts.story.ActRemoveCamera("SpiderCam_CU"))
            (Scripts.story.ActSetCamera("SpiderCam_Side"))
            ("ShowDialogue", "It's strange, don't you think? Who could resist the beauty of Spider Isle?")
        )
        self.anim_welcome.play(s, 50, 60)
        scancel.add_predecessor(s)

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "I just love the salt forest. And you won't believe this...")
        )
        self.anim_welcome.play(s, 70, 120)
        scancel.add_predecessor(s)

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "... Treasure simply washes up on the shore! Ha ha!")
            (bat.story.ActSound('//Sound/sdr.consider3.ogg', vol=3))
        )
        self.anim_welcome.play(s, 130, 150)
        scancel.add_predecessor(s)

        # START SPLIT 1
        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", ("This is my latest find. Isn't it marvelous?",
                ("Can I have it?", "Hey, my \[shell] was taken, so...")))
            (bat.story.ActSound('//Sound/sdr.consider2.ogg', vol=3))
            (bat.story.State()
                (bat.story.CondActionGE(Spider.L_ANIM, 163, tap=True))
                (Scripts.story.ActSetCamera("SpiderCam_Wheel"))
            )
        )
        self.anim_welcome.play(s, 160, 170)
        s.add_successor(scancel)

        sask = (s.create_successor("bar")
            (bat.story.CondActionGE(Spider.L_ANIM, 170))
            (bat.story.CondEventEq("DialogueDismissed", 0, self))
            (Scripts.story.ActRemoveCamera("SpiderCam_Wheel"))
            ("ShowDialogue", "Oh ho, you must be joking!")
            (bat.story.ActSound('//Sound/sdr.bossy1.ogg', vol=3))
        )
        self.anim_rude.play(sask, 1, 30)
        sask.add_successor(scancel)

        ssob = (s.create_successor("sobstory")
            (bat.story.CondActionGE(Spider.L_ANIM, 170))
            (bat.story.CondEventEq("DialogueDismissed", 1, self))
            (Scripts.story.ActRemoveCamera("SpiderCam_Wheel"))
            ("ShowDialogue", "Oh, what a nuisance. He is indeed a pesky bird.")
            (bat.story.ActSound('//Sound/sdr.exasperated1.ogg', vol=3))
        )
        self.anim_nice.play(ssob, 1, 30)
        ssob.add_successor(scancel)

        # END SPLIT 1; START SPLIT 2
        s = (bat.story.State()
            (bat.story.CondActionGE(Spider.L_ANIM, 30))
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", ("But no, I can't just give it to you. It is too precious.",
                ("I'll be your best friend.", "You're not even using it!")))
        )
        self.anim_welcome.play(s, 180, 200, blendin=10)
        ssob.add_successor(s)
        sask.add_successor(s)
        s.add_successor(scancel)

        splead = (s.create_successor("plead")
            (bat.story.CondActionGE(Spider.L_ANIM, 200))
            (bat.story.CondEventEq("DialogueDismissed", 0, self))
            ("ShowDialogue", "Oh! Well then... let's play a game.")
            (bat.story.ActSound('//Sound/sdr.grumble5.ogg', vol=3))
        )
        self.anim_nice.play(splead, 40, 100)
        splead.add_successor(scancel)

        splead = (splead.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 100))
            (bat.story.CondEvent("DialogueDismissed", self))
        )

        sdemand = (s.create_successor("demand")
            (bat.story.CondActionGE(Spider.L_ANIM, 200))
            (bat.story.CondEventEq("DialogueDismissed", 1, self))
            ("ShowDialogue", "What a rude snail you are! You shall not have it.")
            (bat.story.ActSound('//Sound/sdr.bossy2.ogg', vol=3))
            (bat.story.State()
                (bat.story.CondActionGE(Spider.L_ANIM, 74, tap=True))
                (Scripts.story.ActSetCamera("SpiderCam_ECU"))
            )
        )
        self.anim_rude.play(sdemand, 40, 100)
        sdemand.add_successor(scancel)

        sdemand = (sdemand.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 80))
            (bat.story.CondEvent("DialogueDismissed", self))
            (Scripts.story.ActRemoveCamera("SpiderCam_ECU"))
            ("ShowDialogue", "But allow me to taunt you. Hehehe...")
        )
        self.anim_rude.play(sdemand, 110, 150)
        sdemand.add_successor(scancel)

        sdemand = (sdemand.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 150))
            (bat.story.CondEvent("DialogueDismissed", self))
        )

        s = (bat.story.State()
            ("ShowDialogue", "If you can touch the wheel \[wheel], you can keep it.")
            (Scripts.story.ActSetFocalPoint("Wheel_Icon"))
            (bat.story.ActAttrSet("visible", True, ob="Wheel_Icon"))
            (bat.story.ActAction("Wheel_IconAction", 210, 280, ob="Wheel_Icon"))
        )
        self.anim_welcome.play(s, 210, 280, blendin=7)
        splead.add_successor(s)
        sdemand.add_successor(s)
        s.add_successor(scancel)
        # END SPLIT 2

        s = (s.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 260))
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "But we both know it's going to be tricky!")
            (bat.story.ActSound('//Sound/sdr.grumble6.ogg', vol=3))
            (bat.story.ActAttrSet("visible", False, ob="Wheel_Icon"))
            (Scripts.story.ActRemoveFocalPoint('Wheel_Icon'))
        )
        self.anim_welcome.play(s, 290, 330)
        scancel.add_predecessor(s)

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            (bat.story.ActStoreSet('/game/level/spiderWelcome1', True))
            (bat.story.ActStoreSet('/game/storySummary', 'spiderWelcome1'))
        )

        sconv_end = bat.story.State()
        sconv_end.add_predecessor(s)
        sconv_end.add_predecessor(scancel)

        s = (sconv_end.create_successor("Clean up")
            (Scripts.story.ActResumeInput())
            (Scripts.story.ActRemoveFocalPoint('Spider'))
            (Scripts.story.ActRemoveFocalPoint('Wheel_Icon'))
            (Scripts.story.ActRemoveCamera("SpiderCam_Side"))
            (Scripts.story.ActRemoveCamera("SpiderCam_Wheel"))
            (Scripts.story.ActRemoveCamera("SpiderCam_CU"))
            (Scripts.story.ActRemoveCamera("SpiderCam_ECU"))
            (Scripts.story.ActRemoveCamera("SpiderCam"))
        )

        send = s.create_successor("end")
        send.add_condition(bat.story.CondEvent("LeaveWeb", self))

        return sstart, send

    def create_wheel_get_graph(self):
        sstart = (bat.story.State("Get")
            (bat.story.CondEventEq("ShellFound", "Wheel", self))
        )

        s = (sstart.create_successor()
            ("ShowDialogue", "You got the Wheel! It's strong and fast.")
        )

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
            (Scripts.story.ActSuspendInput())
            (Scripts.story.ActSetFocalPoint('Spider'))
            (Scripts.story.ActSetCamera("SpiderCam_Side"))
        )

        s = (s.create_successor()
            ("ShowDialogue", "Good gracious!")
            (bat.story.ActSound('//Sound/sdr.interest1.ogg', vol=4))
        )
        self.anim_get.play(s, 1, 45)

        s = (s.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 45))
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "... I must admit, I'm impressed. I didn't expect you to be able to reach it.")
        )
        self.anim_get.play(s, 50, 80)

        s = (s.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 75))
            (bat.story.CondEvent("DialogueDismissed", self))
            ("ShowDialogue", "But I am a lady of my word. Keep it. May it serve you well.")
            (bat.story.ActSound('//Sound/sdr.grumble4.ogg', vol=3))
        )
        self.anim_get.play(s, 90, 130)

        s = (s.create_successor()
            (bat.story.CondActionGE(Spider.L_ANIM, 130))
            (bat.story.CondEvent("DialogueDismissed", self))
            (bat.story.ActStoreSet('/game/storySummary', 'gotWheel'))
        )

        s = (s.create_successor("Clean up")
            (Scripts.story.ActResumeInput())
            (Scripts.story.ActRemoveFocalPoint('Spider'))
            (Scripts.story.ActRemoveCamera("SpiderCam_Side"))
        )

        send = s.create_successor("end")

        return sstart, send

    def create_after_wheel_graph(self):
        sstart = (bat.story.State("Get")
            (Scripts.story.CondHasShell("Wheel"))
            (bat.story.CondEvent("ApproachWeb", self))
        )

        s = (sstart.create_successor()
            (Scripts.story.ActSuspendInput())
            (Scripts.story.ActSetFocalPoint('Spider'))
            (Scripts.story.ActSetCamera("SpiderCam_Side"))
        )

        s = (s.create_successor()
            ("ShowDialogue", "How is the new shell? It looks like fun.")
            (bat.story.ActSound('//Sound/sdr.greet1.ogg', vol=3))
        )

        s = (s.create_successor()
            (bat.story.CondEvent("DialogueDismissed", self))
        )

        s = (s.create_successor("Clean up")
            (Scripts.story.ActResumeInput())
            (Scripts.story.ActRemoveFocalPoint('Spider'))
            (Scripts.story.ActRemoveCamera("SpiderCam_Side"))
        )

        send = s.create_successor("end")

        return sstart, send

    def get_focal_points(self):
        return [self.children['Spider_Face'], self]


class FlyingCutscene(bat.story.Chapter, bat.bats.BX_GameObject, bge.types.KX_GameObject):

    def __init__(self, old_owner):
        bat.story.Chapter.__init__(self, old_owner)
        self.create_state_graph()

    def create_state_graph(self):
        # This state is executed as a sub-step of other states. That is, it
        # runs every frame while those states are active to make sure the snail
        # trapped.
        snail_holder = bat.story.State("Snail hold")
        snail_holder.add_action(bat.story.ActGeneric(self.hold_snail))

        # Far shot.
        s = self.rootState.create_successor("Init")
        s.add_action(Scripts.story.ActSetCamera("FC_SideCamera"))
        s.add_action(Scripts.story.ActSuspendInput())

        # Close-up
        s = s.create_successor("Transition")
        s.add_condition(bat.story.CondWait(0.5))
        s.add_action(Scripts.story.ActSetCamera("FC_Camera"))
        s.add_action(Scripts.story.ActSetFocalPoint("FC_SnailFlyFocus"))
        s.add_sub_step(snail_holder)

        # Flying through the air.
        s = s.create_successor("Warp speed")
        s.add_condition(bat.story.CondNextFrame())
        s.add_action(bat.story.ActAction("FC_AirstreamAction", 1, 51, 0, ob="FC_Airstream"))
        s.add_action(bat.story.ActAction("FC_CameraAction", 1, 51, 0, ob="FC_Camera"))
        s.add_action(bat.story.ActAction("FC_SnailFlyAction", 1, 100, 0, ob="FC_SnailFly"))
        s.add_sub_step(snail_holder)

        # Shoot the snail through the web. Note that the snail_holder sub-state
        # is no longer used.
        s = s.create_successor("Pick up wheel")
        s.add_condition(bat.story.CondActionGE(0, 49, ob="FC_Airstream"))
        s.add_action(Scripts.story.ActRemoveCamera("FC_Camera"))
        s.add_action(Scripts.story.ActRemoveFocalPoint("FC_SnailFlyFocus"))
        s.add_action(bat.story.ActGeneric(self.shoot_snail))

        s = s.create_successor("Clean up")
        s.add_condition(bat.story.CondNextFrame())
        s.add_condition(bat.story.CondWait(1))
        s.add_action(Scripts.story.ActRemoveCamera("FC_SideCamera"))
        s.add_action(Scripts.story.ActResumeInput())
        s.add_action(bat.story.ActDestroy())

    def hold_snail(self):
        snail = Scripts.director.Director().mainCharacter
        anchor = self.scene.objects['FC_SnailShoot']
        bat.bmath.copy_transform(anchor, snail)
        snail.localLinearVelocity = bat.bmath.MINVECTOR

    def shoot_snail(self):
        snail = Scripts.director.Director().mainCharacter
        anchor = self.scene.objects['FC_SnailShoot']
        bat.bmath.copy_transform(anchor, snail)
        snail.localLinearVelocity = bat.bmath.YAXIS * 75.0
