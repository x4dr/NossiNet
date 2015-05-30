__author__ = 'maric'

import collections


class Character(object):
    def __init__(self, strength=0, dexterity=0, stamina=0, charisma=0, manipulation=0, appearance=0, perception=0,
                 intelligence=0, wits=0, abilities=[]):
        self.strength = strength
        self.dexterity = dexterity
        self.stamina = stamina
        self.charisma = charisma
        self.manipulation = manipulation
        self.appearance = appearance
        self.perception = perception
        self.intelligence = intelligence
        self.wits = wits
        self.abilities = abilities

    def getattributes(self):
        return collections.OrderedDict(strength=self.strength, dexterity=self.dexterity, stamina=self.stamina,
                                       charisma=self.charisma, manipulation=self.manipulation,
                                       appearance=self.appearance, perception=self.perception,
                                       intelligence=self.intelligence, wits=self.wits)

    def getphysical(self):
        return collections.OrderedDict(strength=self.strength, dexterity=self.dexterity, stamina=self.stamina)

    def getsocial(self):
        return collections.OrderedDict(charisma=self.charisma, manipulation=self.manipulation,
                                       appearance=self.appearance)

    def getmental(self):
        return collections.OrderedDict(perception=self.perception, intelligence=self.intelligence, wits=self.wits)

    def getabilities(self):
        return self.abilities


if __name__ == '__main__':
    test = Character()
    pass
