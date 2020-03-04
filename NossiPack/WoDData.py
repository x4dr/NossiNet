one = "#1d1e1"


# noinspection PyPep8Naming
def disciplines(char):
    result = {}
    Animalism = int(char.get("Animalism", 0))
    if Animalism > 0:
        result["Animalism1"] = "#Manipulation#AnimalKen"
    if Animalism > 1:
        result["Animalism2"] = "#Charisma#Survival"
    if Animalism > 2:
        if int(char.get("Intimidation", 0)) > int(char.get("Intimidation", 0)):
            result["Animalism3"] = "#Manipulation#Intimidation"
        else:
            result["Animalism3"] = "#Manipulation#Empathy"
    if Animalism > 3:
        result["Animalism4"] = "#Manipulation#AnimalKen"
    if Animalism > 4:
        result["Animalism5"] = "#Manipulation#SelfControl"

    Auspex = int(char.get("Auspex", 0))
    if Auspex > 0:
        result["Auspex1"] = "#Auspex"
    if Auspex > 1:
        result["Auspex2"] = "#Perception Empathy f8"
    if Auspex > 2:
        result["Auspex3"] = "#Perception Empathy f"  # needs a difficulty at castk time
    if Auspex > 3:
        result["Auspex4"] = "#Intelligence Subterfuge f"
    if Auspex > 4:
        result["Auspex5"] = "#Perception Alertness f"

    Celerity = int(char.get("Celerity", 0))
    # grants extra dice, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if Celerity > 0:
        result["dex"] = "Dexterity Celerity dexbonus"

    Chimerstry = int(char.get("Chimerstry", 0))
    if Chimerstry > 0:
        result["Chimerstry1"] = one
    if Chimerstry > 1:
        result["Chimerstry2"] = one
    if Chimerstry > 2:
        result["Chimerstry3"] = one
    if Chimerstry > 3:
        result["Chimerstry4"] = one
    if Chimerstry > 4:
        result["Chimerstry5"] = "#Manipulation#Subterfuge"

    Dementation = int(char.get("Dementation", 0))
    if Dementation > 0:
        result["Dementation1"] = "#Charisma#Empathy"
    if Dementation > 1:
        result["Dementation2"] = "#Manipulation#Subterfuge"
    if Dementation > 2:
        result["Dementation3"] = "#Perception#Occult"
    if Dementation > 3:
        result["Dementation4"] = "#Manipulation#Empathy f7"
    if Dementation > 4:
        result["Dementation5"] = "#Manipulation#Intimidation"

    Dominate = int(char.get("Dominate", 0))
    if Dominate > 0:
        result["Dominate1"] = "#Manipulation#Intimidation"
    if Dominate > 1:
        result["Dominate2"] = "#Manipulation#Leadership"
    if Dominate > 2:
        result["Dominate3"] = "#Wits#Subterfuge"
    if Dominate > 3:
        result["Dominate4"] = "#Charisma#Leadership"
    if Dominate > 4:
        result["Dominate5"] = "#Charisma#Intimidation"

    Flight = int(char.get("Flight", 0))
    # TODO
    # has no roll associated, remove or employ house-rules?
    if Flight > 0:
        result["Flight1"] = one

    if Flight > 1:
        result["Flight2"] = one

    if Flight > 2:
        result["Flight3"] = one

    if Flight > 3:
        result["Flight4"] = one

    if Flight > 4:
        result["Flight5"] = one

    Fortitude = int(char.get("Fortitude", 0))
    # TODO
    # grants extra dice for soaks, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if Fortitude > 0:
        result["sta"] = "Stamina Fortitude stabonus"
        result["Fortitude1"] = one

    if Fortitude > 1:
        result["Fortitude2"] = one

    if Fortitude > 2:
        result["Fortitude3"] = one

    if Fortitude > 3:
        result["Fortitude4"] = one

    if Fortitude > 4:
        result["Fortitude5"] = one

    Melpominee = int(char.get("Melpominee", 0))
    if Melpominee > 0:  # TODO
        result["Melpominee1"] = one
        # automatic, no roll
    if Melpominee > 1:
        result["Melpominee2"] = "#Wits#Performance f7"  # spend 1 blood
    if Melpominee > 2:
        result["Melpominee3"] = "#Charisma#Performance f7"
    if Melpominee > 3:
        result["Melpominee4"] = "#Manipulation#Performance"
        # Extended, resisted roll, Diff depending on target #Willpower
        # Resisted with Willpower roll (difficulty equal to the singer’s #Appearance#Performance)
    if Melpominee > 4:
        result[
            "Melpominee5"
        ] = "#Stamina#Performance d1e1"  # spend 1 blood for every five targets beyond the first
    # TODO level 6 and 7

    Mytherceria = int(char.get("Mytherceria", 0))
    if Mytherceria > 0:  # TODO
        result["Mytherceria1"] = one
        # deliberate auto-success, no roll
    if Mytherceria > 1:
        result["Mytherceria2"] = one
        # automatic, no roll
    if Mytherceria > 2:
        result["Mytherceria3"] = "#Perception#Empathy"  # diff at GM discretion
    if Mytherceria > 3:
        result["Mytherceria4"] = "#Intelligence#Larceny f7"
        # for inanimate object. use subject’s current Willpower +2 otherwise
        # resist with #Wits#Investigation f8
    if Mytherceria > 4:
        result[
            "Mytherceria5"
        ] = "#Manipulation#Occult"  # difficulty is the victim’s current Willpower
        # TODO level 6,7 and 8

    Necromancy = int(char.get("Necromancy", 0))
    if Necromancy > 0:  # hausregeln!
        result["Necromancy1"] = "#Perception#Alertness f5"
    if Necromancy > 1:
        result["Necromancy2"] = "#Manipulation#Occult"
    if Necromancy > 2:
        result["Necromancy3"] = "#Occult"
    if Necromancy > 3:
        result["Necromancy4"] = "#Willpower"
    if Necromancy > 4:
        result["Necromancy5"] = one

    Obeah = int(char.get("Obeah", 0))
    if Obeah > 0:  # TODO
        result["Obeah1"] = "#Perception#Empathy f7"
    if Obeah > 1:
        result[
            "Obeah2"
        ] = "#Willpower"  # for willing subject, #Willpower f8 otherwise, spend 1 blood in any case
    if Obeah > 2:
        result["Obeah3"] = one
        # no roll, spend 1 blood, more for bigger wounds
    if Obeah > 3:
        result["Obeah4"] = one
        # no roll, spend  two  Willpower
        # resist in extended, resisted Willpower roll battle, first to be 3 successes in front of the other wins
    if Obeah > 4:
        result["Obeah5"] = "#Intelligence#Empathy f8"  # spend  two  blood

    Obfuscate = int(char.get("Obfuscate", 0))
    if Obfuscate > 0:
        result["Obfuscate1"] = "#Dexterity#Stealth"
    if Obfuscate > 1:
        result["Obfuscate2"] = "#Dexterity#Stealth"
    if Obfuscate > 2:
        result["Obfuscate3"] = "#Manipulation#Performance f7"
    if Obfuscate > 3:
        result["Obfuscate4"] = "#Charisma#Stealth"
    if Obfuscate > 4:
        result["Obfuscate5"] = "#Stealth d1e1"

    Obtenebration = int(char.get("Obtenebration", 0))
    if Obtenebration > 0:
        result["Obtenebration1"] = one

    if Obtenebration > 1:
        result["Obtenebration2"] = "#Manipulation#Occult f7"
    if Obtenebration > 2:
        result["Obtenebration3"] = "#Manipulation#Occult f7"
    if Obtenebration > 3:
        result["Obtenebration4"] = "#Manipulation#Courage f7"
    if Obtenebration > 4:
        result["Obtenebration5"] = one

    Potence = int(char.get("Potence", 0))
    # TODO
    # grants extra dice for strength rolls, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if Potence > 0:
        result["str"] = "Strength Potence strbonus"
        result["Potence1"] = one

    if Potence > 1:
        result["Potence2"] = one

    if Potence > 2:
        result["Potence3"] = one

    if Potence > 3:
        result["Potence4"] = one

    if Potence > 4:
        result["Potence5"] = one

    # TODO levels 6,7 and 8

    Presence = int(char.get("Presence", 0))
    if Presence > 0:
        result["Presence1"] = "#Charisma#Performance f7"
    if Presence > 1:
        result["Presence2"] = "#Charisma#Intimidation"
    if Presence > 2:
        result["Presence3"] = "#Appearance#Empathy"
    if Presence > 3:
        result["Presence4"] = "#Charisma#Subterfuge"
    if Presence > 4:
        result["Presence5"] = one

    Protean = int(char.get("Protean", 0))
    if Protean > 0:
        result["Protean1"] = one
        # no roll
    if Protean > 1:
        result["Protean2"] = one
        # spend 1 blood
    if Protean > 2:
        result["Protean3"] = one
        # spend 1 blood
    if Protean > 3:
        result["Protean4"] = one
        # spend 1 blood, up to 3 to transform faster
    if Protean > 4:
        result["Protean5"] = one
        # spend 1 blood, up to 3 to transform faster
    # TODO levels up to 9

    Quietus = int(char.get("Quietus", 0))
    if Quietus > 0:
        result["Quietus1"] = one

    if Quietus > 1:
        result["Quietus2"] = "#Willpower"
    if Quietus > 2:
        result["Quietus3"] = "#Stamina"
    if Quietus > 3:
        result["Quietus4"] = one

    if Quietus > 4:
        result["Quietus5"] = "#Stamina#Athletics"
    # TODO levels up to 9

    Serpentis = int(char.get("Serpentis", 0))
    if Serpentis > 0:
        result["Serpentis1"] = "#Willpower f9"
    if Serpentis > 1:
        result["Serpentis2"] = one
        # no roll
    if Serpentis > 2:
        result["Serpentis3"] = one
        # spend one blood and one Willpower
    if Serpentis > 3:
        result["Serpentis4"] = one
        # spend 1 blood
    if Serpentis > 4:
        result["Serpentis5"] = one
        # no roll

    Temporis = int(char.get("Temporis", 0))
    if Temporis > 0:
        result["Temporis1"] = one

    if Temporis > 1:
        result["Temporis2"] = one

    if Temporis > 2:
        result["Temporis3"] = one

    if Temporis > 3:
        result["Temporis4"] = one

    if Temporis > 4:
        result["Temporis5"] = one

    Thaumaturgy = int(char.get("Thaumaturgy", 0))
    if Thaumaturgy > 0:
        result["Thaumaturgy1"] = "#Willpower f4"
    if Thaumaturgy > 1:
        result["Thaumaturgy2"] = "#Willpower f5"
    if Thaumaturgy > 2:
        result["Thaumaturgy3"] = "#Willpower f6"
    if Thaumaturgy > 3:
        result["Thaumaturgy4"] = "#Willpower f7"
    if Thaumaturgy > 4:
        result["Thaumaturgy5"] = "#Willpower f8"

    Vicissitude = int(char.get("Vicissitude", 0))
    if Vicissitude > 0:
        result[
            "Vicissitude1"
        ] = "#Intelligence#Medicine"  # spend one blood point for each body part to be changed
        # #Perception#Medicine f8 if trying to imitate someones face or voice
    if Vicissitude > 1:
        result[
            "Vicissitude2"
        ] = "#Dexterity#Medicine"  # spend 1 blood, variable difficulty
    if Vicissitude > 2:
        result[
            "Vicissitude3"
        ] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
    if Vicissitude > 3:
        result["Vicissitude4"] = one
        # no roll, spend two blood points
    if Vicissitude > 4:
        result["Vicissitude5"] = one
        # roll system insufficient, this is all about blood
    # TODO up to level 9

    Visceratica = int(char.get("Visceratica", 0))
    if Visceratica > 0:
        result["Visceratica1"] = one  # spend one blood, +5 stealth for scene
    if Visceratica > 1:
        result["Visceratica2"] = one  # spend 1 blood, variable difficulty
    if Visceratica > 2:
        result[
            "Visceratica3"
        ] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
    if Visceratica > 3:
        result["Visceratica4"] = one  # no roll, spend two blood points
    if Visceratica > 4:
        result[
            "Visceratica5"
        ] = one  # roll system insufficient, this is all about blood

    return result
