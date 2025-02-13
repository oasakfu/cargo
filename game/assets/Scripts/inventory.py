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

import bat.store

class Shells(metaclass=bat.bats.Singleton):
    '''Helper class for handling shell inventory order.'''

    # Shell names are stored in '/game/shellInventory' as a set.
    SHELL_NAMES = ['Shell', 'BottleCap', 'Nut', 'Wheel', 'Thimble']
    RED_THINGS = ['BottleCap', 'Wheel', 'Thimble']
    DEFAULT_SHELLS = ['Shell']
    DEFAULT_EQUIPPED = 'Shell'

    def get_equipped(self):
        '''Get the name of the shell that is being carried.'''
        return bat.store.get('/game/equippedShell', Shells.DEFAULT_EQUIPPED)

    def equip(self, name):
        '''Set the name of the shell that is being carried. If it is not already
        in the inventory, it will be added.'''
        self.add(name)
        bat.store.put('/game/equippedShell', name)

    def unequip(self):
        '''Remove the current shell. This does not remove it from the
        inventory.'''
        bat.store.put('/game/equippedShell', None)

    @staticmethod
    def shellkey(item):
        '''Used to sort a list of shells into the same order as SHELL_NAMES.'''
        return Shells.SHELL_NAMES.index(item)

    def add(self, name):
        '''Add a shell to the inventory. This does not equip it.'''
        shells = self.get_shells()
        if not name in shells:
            shells.append(name)
            shells.sort(key=Shells.shellkey)
            bat.store.put('/game/shellInventory', shells)

    def discard(self, name):
        '''Remove a shell from the inventory. If it is equipped, it will be
        unequipped.'''
        if bat.store.get('/game/equippedShell', None) == name:
            self.unequip()

        shells = self.get_shells()
        if name in shells:
            shells.remove(name)
            bat.store.put('/game/shellInventory', shells)

    def get_shells(self):
        '''Get a list of all shells in the inventory.'''
        return bat.store.get('/game/shellInventory', Shells.DEFAULT_SHELLS)

    def get_all_shells(self):
        return Shells.SHELL_NAMES

    def remaining_shells(self):
        red_things = set(self.RED_THINGS)
        return red_things.difference(self.get_shells())

    def get_next(self, offset):
        '''Get the next shell, relative to the equipped one. If no shell
        is equipped, the first shell is returned. If no shells are in the
        inventory, None is returned.'''
        equipped = self.get_equipped()
        shells = self.get_shells()
        if len(shells) == 0:
            return None

        try:
            index = shells.index(equipped)
            return shells[(index + offset) % len(shells)]
        except ValueError:
            if offset < 0:
                offset = (offset + 1) % len(shells)
            elif offset > 0:
                offset = (offset - 1) % len(shells)
            return shells[offset]
