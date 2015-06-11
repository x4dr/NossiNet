from random import Random
import urllib
import re

from NossiPack.krypta import randomlyspend

__author__ = 'maric'

import collections


class Character(object):
    def __init__(self, name="", strength=0, dexterity=0, stamina=0, charisma=0, manipulation=0, appearance=0,
                 perception=0, intelligence=0, wits=0, abilities=[]):
        self.name = name
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
        result = collections.OrderedDict()
        result['strength'] = self.strength
        result['dexterity'] = self.dexterity
        result['stamina'] = self.stamina
        result['charisma'] = self.charisma
        result['manipulation'] = self.manipulation
        result['appearance'] = self.appearance
        result['perception'] = self.perception
        result['intelligence'] = self.intelligence
        result['wits'] = self.wits
        return result

    def setattributes(self, strength=-1, dexterity=-1, stamina=-1, charisma=-1, manipulation=-1, appearance=-1,
                      perception=-1, intelligence=-1, wits=-1):
        if strength >= 0:
            self.strength = strength
        if dexterity >= 0:
            self.dexterity = dexterity
        if stamina >= 0:
            self.stamina = stamina
        if charisma >= 0:
            self.charisma = charisma
        if manipulation >= 0:
            self.manipulation = manipulation
        if appearance >= 0:
            self.appearance = appearance
        if perception >= 0:
            self.perception = perception
        if intelligence >= 0:
            self.intelligence = intelligence
        if wits >= 0:
            self.wits = wits

    def getabilityscore(self, ability):
        for a in self.abilities:
            if a[0] == ability:
                return a[1]
        return 0

    def setabilityscore(self, ability, score):
        for a in self.abilities:
            if a[0] == ability:
                a[1] = score
                return
        a.append([ability, score])
        return

    def getphysical(self):
        return collections.OrderedDict(strength=self.strength, dexterity=self.dexterity, stamina=self.stamina)

    def setphysical(self, attributes):
        self.setattributes(strength=attributes[0], dexterity=attributes[1], stamina=attributes[2])

    def getsocial(self):
        return collections.OrderedDict(charisma=self.charisma, manipulation=self.manipulation,
                                       appearance=self.appearance)

    def setsocial(self, attributes):
        self.setattributes(charisma=attributes[0], manipulation=attributes[1], appearance=attributes[2])

    def getmental(self):
        return collections.OrderedDict(perception=self.perception, intelligence=self.intelligence, wits=self.wits)

    def setmental(self, attributes):
        self.setattributes(perception=attributes[0], intelligence=attributes[1], wits=attributes[2])

    def getabilities(self):
        return self.abilities

    def getstringrepr(self):
        result = "Name ideas: " + self.name + "\n"
        for i in range(len(self.getattributes()) // 3):
            result += \
                str(list(self.getattributes().keys())[i]).rjust(12) + ": " + \
                str(list(self.getattributes().values())[i]) + "\t   " + \
                str(list(self.getattributes().keys())[i + 3]).rjust(12) + ": " + \
                str(list(self.getattributes().values())[i + 3]) + "\t  " + \
                str(list(self.getattributes().keys())[i + 6]).rjust(12) + ": " + \
                str(list(self.getattributes().values())[i + 6]) + "\t  " + "\n"
        return result


def makechar(min, cap, prioa, priob, prioc):
    response = urllib.request.urlopen(
        "http://www.behindthename.com/random/random.php?number=2&gender=both&surname=&randomsurname=yes&all=no&"
        "usage_ger=1&usage_myth=1&usage_anci=1&usage_bibl=1&usage_hist=1&usage_lite=1&usage_theo=1&usage_goth=1&"
        "usage_fntsy=1")
    char = Character()
    prio = [prioa, priob, prioc]
    Random().shuffle(prio)
    print(prio)
    char.setphysical(randomlyspend(3, min, cap, prio[0]))
    char.setsocial(randomlyspend(3, min, cap, prio[1]))
    char.setmental(randomlyspend(3, min, cap, prio[2]))

    names = re.compile('<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......')
    a = str(response.read())

    result = names.search(a)
    try:
        char.name = (result.group(1) + ", " + result.group(2) + ", " + result.group(3))
    except:
        char.name = "think for yourself"
    return char


if __name__ == '__main__':
    pass
    for x in range(100):
        test = chargen(0, 3, 5, 7)
        print(test.getstringrepr())
