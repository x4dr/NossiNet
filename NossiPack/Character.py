import collections
import logging
import pickle
import re
import time
from random import Random
from urllib import request

from gamepack.Dice import DescriptiveError

from Data import getlocale_data
from NossiPack.VampireCharacter import intdef

logger = logging.getLogger(__name__)
__author__ = "maric"


# Database still uses this, legacy support
# noinspection DuplicatedCode
class Character:
    def __init__(
        self,
        name="",
        attributes=None,
        meta=None,
        abilities=None,
        virtues=None,
        backgrounds=None,
        disciplines=None,
        special=None,
    ):
        self.name = name
        if attributes is None:
            self.attributes = self.zero_attributes()
        else:
            self.attributes = attributes
        if abilities is None:
            self.abilities = self.zero_abilities()
        else:
            self.abilities = abilities
        if meta is None:
            self.meta = self.zero_meta()
        else:
            self.meta = meta
        if backgrounds is None:
            self.backgrounds = collections.OrderedDict()
        else:
            self.backgrounds = backgrounds
        if disciplines is None:
            self.disciplines = collections.OrderedDict()
        else:
            self.disciplines = disciplines
        if virtues is None:
            self.virtues = self.zero_virtues()
        else:
            self.virtues = virtues
        if special is None:
            self.special = self.zero_specials()
        else:
            self.special = special

        self.timestamp = time.strftime("%Y/%m/%d-%H:%M:%S")

    @staticmethod
    def calc_cost(val1, val2, cost, cost0):
        lower = min(val1, val2)
        higher = max(val1, val2)
        result = 0
        while (higher - lower) > 0:
            if lower == 0:
                result += cost0
                lower += 1
                continue
            result += cost * lower
            lower += 1
        return result

    def checksum(self):
        result = 0
        for a in self.unify().values():
            try:
                result += int(a)
            except Exception:
                raise DescriptiveError("could not add up", a)
        return result

    @staticmethod
    def get_clans():
        return {
            "Assamite": "Celerity, Obfuscate, Quietus",
            "Brujah": "Celerity, Potence, Presence",
            "Setite": "Obfuscate, Presence, Serpentis",
            "Gangrel": "Animalism, Fortitude, Protean",
            "Giovanni": "Dominate, Necromancy, Potence",
            "Lasombra": "Dominate, Obtenebration, Potence",
            "Malkavian": "Auspex, Dementation, Obfuscate",
            "Nosferatu": "Animalism, Obfuscate, Potence",
            "Ravnos": "Animalism, Chimerstry, Fortitude",
            "Toreador": "Auspex, Celerity, Presence",
            "Tremere": "Auspex, Dominate, Thaumaturgy",
            "Tzimisce": "Animalism, Auspex, Vicissitude",
            "Ventrue": "Dominate, Fortitude, Presence",
            "Daughter of Cacophony": "Fortitude, Melpominee, Presence",
            "Gargoyle": "Flight, Fortitude, Potence, Vicissitude",
            "Kiasyd": "Dominate, Mytherceria, Obtenebration",
            "Salubri": "Auspex, Fortitude, Obeah",
            "Sage": "Potence, Presence, Temporis",
            "Cappadocian": "Auspex, Fortitude, Necromancy",
        }

    def get_clandisciplines(self):
        return self.get_clans().get(self.meta["Clan"], "No Clan")

    @staticmethod
    def get_backgrounds():
        return [
            "Allies",
            "Contacts",
            "Retainers",
            "Resources",
            "Status",
            "Influence",
            "Generation",
            "Domain",
            "Fame",
            "Herd",
            "Mentor",
        ]

    def set_attributes_from_int_list(self, att):
        self.attributes["Strength"] = att[0]
        self.attributes["Dexterity"] = att[1]
        self.attributes["Stamina"] = att[2]

        self.attributes["Charisma"] = att[3]
        self.attributes["Manipulation"] = att[4]
        self.attributes["Appearance"] = att[5]

        self.attributes["Perception"] = att[6]
        self.attributes["Intelligence"] = att[7]
        self.attributes["Wits"] = att[8]

    def set_abilities_from_int_list(self, abi):
        i = 0
        for c in reversed(sorted(self.abilities.keys())):
            for a in sorted(self.abilities[c].keys()):
                self.abilities[c][a] = abi[i]
                i += 1

    def validate_char(self, extra=False):
        def need(name, number):
            return name + f" still needs {abs(int(number)):d} points allocated. \n"

        freebs = 15
        comment = ""
        if self.meta["Clan"] == "Nosferatu":
            self.attributes["Appearance"] = 0
        att = [
            self.attributes["Strength"]
            + self.attributes["Dexterity"]
            + self.attributes["Stamina"],
            self.attributes["Charisma"]
            + self.attributes["Manipulation"]
            + self.attributes["Appearance"],
            self.attributes["Perception"]
            + self.attributes["Intelligence"]
            + self.attributes["Wits"],
        ]
        if self.meta["Clan"] == "Nosferatu":
            att[1] += 1  # clan weakness
        att.sort()
        attgrphigh = att[2] - 10
        attgrpmedium = att[1] - 8
        attgrplow = att[0] - 6
        if attgrphigh < 0:
            comment += need("The highest priority attribute group", attgrphigh)
        if attgrpmedium < 0:
            comment += need("The medium priority attribute group", attgrpmedium)
        if attgrplow < 0:
            comment += need("The lowest priority attribute group", attgrplow)

        ski = 0
        skil = 0
        for i in self.abilities["Skills"].values():
            ski += i
            skil += min(3, i)
            if i == 5:
                comment += "No ability at 5 at the start of the game!\n"
        kno = 0
        knol = 0
        for i in self.abilities["Knowledges"].values():
            kno += i
            knol += min(3, i)
        tal = 0
        tall = 0
        for i in self.abilities["Talents"].values():
            tal += i
            tall += min(3, i)
        abil = [skil, knol, tall]
        abil.sort()
        abilgrphigh = abil[2] - 13
        abilgrpmedium = abil[1] - 9
        abilgrplow = abil[0] - 5
        abi = [ski, kno, tal]
        abi.sort()
        abigrphigh = abi[2] - 13
        abigrpmedium = abi[1] - 9
        abigrplow = abi[0] - 5
        if abilgrphigh < 0:
            comment += need("The highest priority ability group", abilgrphigh)
            if abigrphigh - abilgrphigh != 0:
                comment += "(maximum before freebies is 3)\n"
        if abilgrpmedium < 0:
            comment += need("The medium priority ability group", abilgrpmedium)
            if abigrpmedium - abilgrpmedium != 0:
                comment += "(maximum before freebies is 3)\n"
        if abilgrplow < 0:
            comment += need("The lowest priority ability group", abilgrplow)
            if abigrplow - abilgrplow != 0:
                comment += "(maximum before freebies is 3)\n"

        bac = 0
        vir = 0
        dis = 0
        for b in self.backgrounds.values():
            bac += b
        for v in self.virtues.values():
            vir += v
        for d in self.disciplines.values():
            dis += d
        bac -= 5
        vir -= 10
        dis -= 3
        if bac < 0:
            comment += need("The Background section", bac)
        if vir < 0:
            comment += need("The Virtues section", vir)
        if dis < 0:
            comment += need("The Discipline section", dis)
        hum = (
            self.special["Humanity"]
            - self.virtues["Conscience"]
            - self.virtues["SelfControl"]
        )
        wil = self.special["Willmax"] - self.virtues["Courage"]

        if hum < 0:
            comment += need("Humanity", hum)
        if wil < 0:
            comment += need("Willpower", wil)
        if comment == "":
            freebs = (
                freebs
                - attgrphigh * 5
                - attgrpmedium * 5
                - attgrplow * 5
                - abigrphigh * 2
                - abigrpmedium * 2
                - abigrplow * 2
                - bac * 1
                - vir * 2
                - dis * 7
                - hum * 1
                - wil * 1
            )
            if freebs < 0:
                comment = f"You have spend {-freebs:d} Freebies too many!\n "
            if freebs > 0:
                comment = f"You have {freebs:d} Freebies left!\n"
            if freebs == 0 and extra:
                comment = "This character is a valid starting character.\n"
            if freebs < 15 and extra:
                comment += "Freebies spent:\n" "High Attribute Group: \t " + str(
                    attgrphigh * 5
                ) + "\n" + "Medium Attribute Group:\t " + str(
                    attgrpmedium * 5
                ) + "\n" + "Low Attribute Group: \t " + str(
                    attgrplow * 5
                ) + "\n" + "High Ability Group: \t " + str(
                    abigrphigh * 2
                ) + "\n" + "Medium Ability Group: \t " + str(
                    abigrpmedium * 2
                ) + "\n" + "Low Ability Group: \t " + str(
                    abigrplow * 2
                ) + "\n" + "Background Section: \t " + str(
                    bac * 1
                ) + "\n" + "Discipline Section: \t " + str(
                    dis * 7
                ) + "\n" + "Virtues: \t \t " + str(
                    vir * 2
                ) + "\n" + "Humanity: \t \t " + str(
                    hum * 1
                ) + "\n" + "Willpower: \t \t " + str(
                    wil * 1
                )
        return comment

    def get_diff(self, old=None, extra=False):
        xpdiff = 0
        if old is None:
            return self.validate_char(extra)

        for a in self.attributes.keys():
            xpdiff += self.calc_cost(self.attributes[a], old.attributes[a], 4, 1000)
        for b in self.abilities.keys():
            for a in self.abilities[b].keys():
                xpdiff += self.calc_cost(
                    self.abilities[b][a], old.abilities[b][a], 2, 3
                )
        for a in self.disciplines.keys():
            c = 7
            b = self.get_clandisciplines()
            if b == "No Clan":
                c = 6
            elif a in b:
                c = 5
            xpdiff += self.calc_cost(
                self.disciplines[a], old.disciplines.get_str(a, 0), c, 10
            )

        xpdiff += self.calc_cost(
            self.special["Willmax"], old.special["Willmax"], 1, 1000
        )
        if extra:
            result = f"To upgrade the sheet from {old.timestamp} to this one would cost {xpdiff:d} XP."
        else:
            result = xpdiff
        return result

    def dictlist(self):
        special = {}
        for i in self.special.keys():
            try:
                special[i] = int(
                    self.special[i]
                )  # legacy ... rework might be as easy as removing this
            except ValueError:
                pass  # sort all numeric values into special

        return [
            self.attributes,
            self.abilities["Skills"],
            self.abilities["Talents"],
            self.abilities["Knowledges"],
            self.virtues,
            self.disciplines,
            special,
        ]

    def unify(self):
        a = self.dictlist()
        result = {}
        for b in a:
            for i in b.keys():
                result[i] = str(b[i])
        return result

    # noinspection PyUnresolvedReferences
    def setfromdalines(self, number):
        dalines = ""

        def getmeta(name):
            value = re.compile(
                name + r':.*?">(.*?)</td>',
                flags=(re.MULTILINE + re.DOTALL + re.IGNORECASE),
            )
            try:
                return value.search(dalines).group(1)
            except Exception:
                return None

        def getval(name):
            name = name.replace(" ", "")
            value = re.compile(
                name + r".*?</td>(.*?)</td>",
                flags=(re.MULTILINE + re.DOTALL + re.IGNORECASE),
            )
            try:
                return value.search(dalines).group().count("checked")
            except Exception:
                logger.error(f"not found in sheet: {name}!")
                return 0

        def getbgdscp():
            section = re.compile(
                r"Backgrounds(.*?)Merit",
                flags=(re.MULTILINE + re.DOTALL + re.IGNORECASE),
            )
            section = section.search(dalines).group(1)
            teedees = re.compile(r"<td>(?:<b>)?(.*?)(?:</b>)?</td>")
            teedees = teedees.findall(section)
            backgroundnames = [0, 3, 5, 7, 10, 12, 14]
            backgroundnames = [teedees[x] for x in backgroundnames]
            disciplinenames = [1, 4, 6, 8, 11, 13, 15]
            disciplinenames = [teedees[x] for x in disciplinenames]
            return backgroundnames, disciplinenames

        def getmthmwp():
            section = re.compile(
                r"Merits(.*?)</table>", flags=(re.MULTILINE + re.DOTALL + re.IGNORECASE)
            )
            section = section.search(dalines).group(1)
            teedees = re.compile(r"<td .*?>(.*?)?</td>")
            teedees = teedees.findall(section)
            _merits = ""
            for i in range(2, 31, 3):
                _merits += teedees[i] + "\n"
            _humanity = teedees[6].count("checked")
            _willpower = teedees[15].count("checked")
            return _merits, _humanity, _willpower

        try:
            number = int(number)
        except Exception:
            try:
                number = int(re.search(r"\D*(.*)", number).group(1))
            except Exception:
                return False

        response = request.urlopen("https://sheetgen.dalines.net/sheet/" + str(number))
        dalines = response.read().decode()

        for a in self.meta.keys():
            b = getmeta(a)
            if b:
                self.meta[a] = b

        bg, dscp = getbgdscp()
        self.disciplines = collections.OrderedDict()
        self.backgrounds = collections.OrderedDict()
        for b in bg:
            self.backgrounds[b] = getval(b)
        for b in dscp:
            self.disciplines[b] = getval(b)
        for b in self.virtues.keys():
            self.virtues[b] = getval(b)

        for a in self.attributes.keys():
            try:
                self.attributes[a] = getval(a)
            except Exception:
                self.attributes[a] = 0

        for b in self.abilities.keys():
            for a in self.abilities[b].keys():
                try:
                    self.abilities[b][a] = getval(a)
                except Exception:
                    self.abilities[b][a] = 0
        merits, humanity, willpower = getmthmwp()
        self.meta["Merits"] = merits
        self.special["Willmax"] = willpower
        self.special["Humanity"] = humanity

        return True

    def setfromform(self, form):  # accesses internal dicts
        self.attributes = self.zero_attributes()
        self.abilities = self.zero_abilities()
        self.disciplines = collections.OrderedDict()
        self.backgrounds = collections.OrderedDict()
        self.special = self.zero_specials()
        self.meta["Generation"] = 13
        self.special["Bloodmax"] = 10
        for field in form:
            value = form[field]
            if field in self.meta.keys():
                if value is not None:
                    self.meta[field] = value
                    if field == "Merits":
                        if "Generation 14" in value:
                            self.meta["Generation"] = 14
                            self.backgrounds["Generation"] = -1
                        if "Generation 15" in value:
                            self.meta["Generation"] = 15
                            self.backgrounds["Generation"] = -2
                continue
            if field in self.attributes.keys():
                if value is not None:
                    self.attributes[field] = intdef(value)
                continue
            if field in self.abilities["Skills"].keys():
                if value is not None:
                    logger.info(f"Skill setting {field} to  {value}")
                    self.abilities["Skills"][field] = intdef(value)
                continue
            if field in self.abilities["Talents"].keys():
                if value is not None:
                    logger.info(f"Talents setting {field} to  {value}")
                    self.abilities["Talents"][field] = intdef(value)
                continue
            if field in self.abilities["Knowledges"].keys():
                if value is not None:
                    logger.info(f"Knowledges setting {field} to  {value}")
                    self.abilities["Knowledges"][field] = intdef(value)
                continue
            if "background_name_" in field:
                if (
                    (value is not None)
                    and (value != "")
                    and (field != "background_name_")
                ):  # no empty submits
                    try:
                        preval = self.backgrounds[value]
                    except Exception:
                        preval = 0
                    try:
                        self.backgrounds[value] = preval + int(
                            form[
                                "background_value_"
                                + re.match(r"background_name_(.*)", field).group(1)
                            ]
                        )
                    except Exception:
                        self.backgrounds[value] = 0
                if value == "Generation":
                    self.meta[value] = str(
                        int(self.meta[value]) - self.backgrounds[value]
                    )
                    self.special["Bloodmax"] = int(10 + self.backgrounds[value])
                    if self.meta[value] == "7":
                        self.special["Bloodmax"] = 20
                    if self.meta[value] == "6":
                        self.special["Bloodmax"] = 30
                    if self.meta[value] == "5":
                        self.special["Bloodmax"] = 50
                    if self.meta[value] == "4":
                        self.special["Bloodmax"] = 100
                    if self.meta[value] == "3":
                        self.special["Bloodmax"] = 250
                    if self.meta[value] == "2":
                        self.special["Bloodmax"] = 1000
                    if self.meta[value] == "1":
                        self.special["Bloodmax"] = 1

                continue
            if "discipline_name_" in field:
                if (value is not None) and (
                    field != "discipline_name_"
                ):  # no empty submits
                    try:
                        preval = self.disciplines[value]
                    except Exception:
                        preval = 0
                    try:
                        self.disciplines[value] = preval + int(
                            form[
                                "discipline_value_"
                                + re.match(r"discipline_name_(.*)", field).group(1)
                            ]
                        )
                    except Exception:
                        self.disciplines[value] = 0
                continue
            if "virtue_name_" in field:
                if (value is not None) and (
                    field != "virtue_name_"
                ):  # no empty submits
                    try:
                        self.virtues[value] = int(
                            form[
                                "virtue_value_"
                                + re.match(r"virtue_name_(.*)", field).group(1)
                            ]
                        )
                    except Exception:
                        self.virtues[value] = 0
                continue
            if "discipline_value_" in field:
                continue
            if "background_value_" in field:
                continue
            if "virtue_value_" in field:
                continue
            if field in self.special.keys() and value is not None:
                self.special[field] = intdef(value)
                continue
            if "newsheet" not in field:
                logger.error(f"error inserting a key! {field} : {value}")

        self.disciplines = collections.OrderedDict(
            x for x in sorted(self.disciplines.items()) if x[0] != ""
        )
        self.backgrounds = collections.OrderedDict(
            x for x in sorted(self.backgrounds.items()) if x[0] != ""
        )

    def applydamage(self, amount, dmg_type="Lethal"):
        if amount > 0:
            self.special[dmg_type] += amount
        else:
            if dmg_type == "Aggravated":
                self.special["Aggravated"] += amount
                if self.special["Aggravated"] <= 0:
                    self.special["Aggravated"] = 0
                    self.special["Partialheal"] = 0
            else:
                self.special["Bashing"] += amount
                if self.special["Bashing"] < 0:
                    self.special["Lethal"] += self.special["Bashing"]
                    self.special["Bashing"] = 0
                if self.special["Lethal"] < 0:
                    self.special["Partialheal"] -= self.special["Lethal"]
                    self.special["Lethal"] = 0
                if self.special["Partialheal"] > 4:
                    self.special["Partialheal"] -= 5
                    self.applydamage(-1, "Aggravated")
        while (
            self.special["Bashing"]
            + self.special["Lethal"]
            + self.special["Aggravated"]
            > 7
        ):
            if dmg_type == "Bashing":  # if damage is bashing
                if self.special["Bashing"] > 1:  # and there already is bashing damage
                    self.special["Bashing"] -= 2  # transform a bashing into lethal
                    self.special["Lethal"] += 1
                else:
                    self.special["Bashing"] = (
                        0  # bashing will not overflow into aggravated
                    )
                    break
            elif dmg_type == "Lethal":
                if self.special["Lethal"] > 1:  # same for lethal to aggravated
                    self.special["Lethal"] -= 2
                    self.applydamage(1, "Aggravated")
            elif dmg_type != "Aggravated":
                raise Exception(dmg_type + "???")

            if self.special["Aggravated"] >= 7:
                raise Exception(
                    self.meta["Name"]
                    + " is ash with "
                    + str(self.special["Aggravated"])
                    + " aggravated damage."
                )

    def process_trigger(self, trigger):
        if "§blood_" in trigger:
            try:
                amount = int(trigger.replace("§blood_", "").strip())
                self.special["Bloodpool"] -= amount
                if self.special["Bloodpool"] > self.special["Bloodmax"]:
                    self.special["Bloodpool"] = self.special["Bloodmax"]
            except Exception:
                raise Exception("Invalid Blood value: " + trigger)
        if "§will_" in trigger:
            try:
                amount = int(trigger.replace("§will_", "").strip())
                self.special["Willpower"] -= amount
                if self.special["Willpower"] > self.special["Willmax"]:
                    self.special["Willpower"] = self.special["Willmax"]
            except Exception:
                raise Exception("Invalid Will value: " + trigger)

        if "§damage_" in trigger:
            try:
                if "_bashing_" in trigger:
                    amount = int(trigger.replace("§damage_bashing_", "").strip())
                    self.applydamage(amount, dmg_type="Bashing")
                elif "_aggravated_" in trigger:
                    amount = int(trigger.replace("§damage_aggravated_", "").strip())
                    self.applydamage(amount, dmg_type="Aggravated")
                else:
                    amount = int(
                        trigger.replace(trigger[: trigger.rfind("_") + 1], "").strip()
                    )
                    self.applydamage(amount)
            except Exception as inst:
                raise Exception(
                    "Invalid damage: " + trigger + ", because " + str(inst.args[0])
                )

        if "§heal_" in trigger:
            try:
                if "§heal_aggravated_" in trigger:
                    amount = int(trigger.replace("§heal_aggravated_", "").strip())
                    self.applydamage(-amount, dmg_type="Aggravated")
                else:
                    amount = int(trigger.replace("§heal_", "").strip())
                    self.applydamage(-amount)
            except Exception:
                raise Exception("Invalid healing: " + trigger)

    def getdictrepr(self):
        character = {
            "Name": self.name,
            "Meta": self.meta,
            "Attributes": self.attributes,
            "Abilities": self.abilities,
            "Disciplines": self.disciplines,
            "Virtues": self.virtues,
            "Backgrounds": self.backgrounds,
            "BGVDSCP_combined": self.combine_bgvdscp(),
            "Special": self.special,
            "Type": "OWOD",
        }
        return character

    def legacy_convert(
        self,
    ):  # this is the legacy section used to update old sheets into new formats
        # Fix: uppercasing attributes
        newatt = self.zero_attributes()
        for i in self.attributes.keys():
            newkey = i[0].upper() + i[1:]
            newatt[newkey] = self.attributes[i]
        self.attributes = newatt
        # Fix: removing space from Self[ ]Control
        try:
            self.virtues["SelfControl"] = self.virtues["Self Control"]
            self.virtues.pop("Self Control", None)
        except Exception:
            pass  # already was converted
        # Fix: adding special partialheal
        try:
            self.special["Partialheal"] = self.special["Partialheal"]
        except Exception:
            self.special["Partialheal"] = 0

    def combine_bgvdscp(self):
        combined = []
        for i in range(
            max(
                len(self.backgrounds),
                len(self.disciplines.keys()),
                len(self.virtues.keys()),
            )
        ):
            combined.append({})
            try:
                combined[i]["Background"] = list(self.backgrounds.keys())[i]
            except Exception:
                combined[i]["Background"] = ""
            try:
                combined[i]["Background_Value"] = self.backgrounds[
                    list(self.backgrounds.keys())[i]
                ]
            except Exception:
                combined[i]["Background_Value"] = 0
            try:
                combined[i]["Discipline"] = list(self.disciplines.keys())[i]
            except Exception:
                combined[i]["Discipline"] = ""
            try:
                combined[i]["Discipline_Value"] = self.disciplines[
                    list(self.disciplines.keys())[i]
                ]
            except Exception:
                combined[i]["Discipline_Value"] = 0
            try:
                combined[i]["Virtue"] = list(self.virtues.keys())[i]
            except Exception:
                combined[i]["Virtue"] = ""
            try:
                combined[i]["Virtue_Value"] = self.virtues[list(self.virtues.keys())[i]]
            except Exception:
                combined[i]["Virtue_Value"] = 0

        return combined

    @staticmethod
    def zero_attributes():
        attributes = {
            "Strength": 0,
            "Dexterity": 0,
            "Stamina": 0,
            "Charisma": 0,
            "Manipulation": 0,
            "Appearance": 0,
            "Perception": 0,
            "Intelligence": 0,
            "Wits": 0,
        }
        return attributes

    @staticmethod
    def zero_abilities():
        return getlocale_data()["abilities"]

    @staticmethod
    def zero_specials():
        special = {
            "Humanity": 0,
            "Willpower": 0,
            "Willmax": 1,
            "Bloodpool": 0,
            "Bloodmax": 10,
            "Partialheal": 0,
            "Bashing": 0,
            "Lethal": 0,
            "Aggravated": 0,
        }
        return special

    @staticmethod
    def zero_meta():
        meta = {
            "Name": "",
            "Nature": "",
            "Generation": "",
            "Player": "",
            "Demeanor": "",
            "Haven": "",
            "Chronicle": "",
            "Clan": "",
            "Concept": "",
            "Notes": "notes",
            "Merits": "merits and flaws",
            "Gear": "Gear",
        }
        return meta

    @staticmethod
    def zero_virtues():
        return collections.OrderedDict(
            {"Conscience": 0, "SelfControl": 0, "Courage": 0}
        )

    def serialize(self):
        return pickle.dumps(self)

    @staticmethod
    def deserialize(serialized):
        tmp = pickle.loads(serialized)
        tmp.legacy_convert()
        return tmp

    @staticmethod
    def makerandom(
        mini, cap, prio1a, prio1b, prio1c, prio2a, prio2b, prio2c, do_shuffle
    ):
        response = request.urlopen(
            "https://www.behindthename.com/random/random.php?number=2&gender=both&"
            "surname=&randomsurname=yes&all=no&usage_ger=1&usage_myth=1&usage_anci=1&"
            "usage_bibl=1&usage_hist=1&usage_lite=1&usage_theo=1&usage_goth=1&"
            "usage_fntsy=1"
        )
        prio = [prio1a, prio1b, prio1c]
        abi = [prio2a, prio2b, prio2c]
        if do_shuffle:
            Random().shuffle(prio)
            Random().shuffle(abi)

        names = re.compile(
            "<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......<a c[^>]*.([^<]*)......"
        )
        a = str(response.read())

        result = names.search(a)
        char = Character()
        att = (
            allocaterandomly(prio[0], mini, cap, 3)
            + allocaterandomly(prio[1], mini, cap, 3)
            + allocaterandomly(prio[2], mini, cap, 3)
        )
        abi = (
            allocaterandomly(abi[0], 0, 3, 10)
            + allocaterandomly(abi[1], 0, 3, 10)
            + allocaterandomly(abi[2], 0, 3, 10)
        )
        char.set_attributes_from_int_list(att)
        char.set_abilities_from_int_list(abi)
        char.set_virtues_from_int_list(allocaterandomly(7, 1, 5, 3))
        try:
            char.meta["Name"] = (
                result.group(1) + " " + result.group(2) + " " + result.group(3)
            )
        except Exception:
            char.name = "choose a name!"
        return char

    def set_virtues_from_int_list(self, vir):
        self.virtues["Conscience"] = vir[0]
        self.virtues["SelfControl"] = vir[1]
        self.virtues["Courage"] = vir[2]


def allocaterandomly(num, mini, cap, var):
    att = [mini] * var
    while num:
        x = Random().randint(0, var - 1)
        if att[x] < cap:
            att[x] += 1
            num -= 1
        else:
            if sum(att) >= cap * var:
                break
    return att


def upsert(listinput, index, value, minimum=3):
    if index >= len(listinput):
        listinput.append("")
        index = len(listinput) - 1
    if value != "":
        listinput[index] = value
    else:
        listinput.pop(index)
    if "".join(listinput[(-1 * minimum) :]):
        listinput.append("")
    return listinput
