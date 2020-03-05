one = "#1d1e1"


def disciplines(char):
    result = {}
    animalism = int(char.get("Animalism", 0))
    if animalism > 0:
        result["Animalism1"] = "#Manipulation#AnimalKen"
    if animalism > 1:
        result["Animalism2"] = "#Charisma#Survival"
    if animalism > 2:
        if int(char.get("Intimidation", 0)) > int(char.get("Intimidation", 0)):
            result["Animalism3"] = "#Manipulation#Intimidation"
        else:
            result["Animalism3"] = "#Manipulation#Empathy"
    if animalism > 3:
        result["Animalism4"] = "#Manipulation#AnimalKen"
    if animalism > 4:
        result["Animalism5"] = "#Manipulation#SelfControl"

    auspex = int(char.get("Auspex", 0))
    if auspex > 0:
        result["Auspex1"] = "#Auspex"
    if auspex > 1:
        result["Auspex2"] = "#Perception empathy f8"
    if auspex > 2:
        result["Auspex3"] = "#Perception empathy f"  # needs a difficulty at castk time
    if auspex > 3:
        result["Auspex4"] = "#Intelligence subterfuge f"
    if auspex > 4:
        result["Auspex5"] = "#Perception alertness f"

    celerity = int(char.get("Celerity", 0))
    # grants extra dice, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if celerity > 0:
        result["dex"] = "Dexterity celerity dexbonus"

    chimerstry = int(char.get("Chimerstry", 0))
    if chimerstry > 0:
        result["Chimerstry1"] = one
    if chimerstry > 1:
        result["Chimerstry2"] = one
    if chimerstry > 2:
        result["Chimerstry3"] = one
    if chimerstry > 3:
        result["Chimerstry4"] = one
    if chimerstry > 4:
        result["Chimerstry5"] = "#Manipulation#Subterfuge"

    dementation = int(char.get("Dementation", 0))
    if dementation > 0:
        result["Dementation1"] = "#Charisma#Empathy"
    if dementation > 1:
        result["Dementation2"] = "#Manipulation#Subterfuge"
    if dementation > 2:
        result["Dementation3"] = "#Perception#Occult"
    if dementation > 3:
        result["Dementation4"] = "#Manipulation#Empathy f7"
    if dementation > 4:
        result["Dementation5"] = "#Manipulation#Intimidation"

    dominate = int(char.get("Dominate", 0))
    if dominate > 0:
        result["Dominate1"] = "#Manipulation#Intimidation"
    if dominate > 1:
        result["Dominate2"] = "#Manipulation#Leadership"
    if dominate > 2:
        result["Dominate3"] = "#Wits#Subterfuge"
    if dominate > 3:
        result["Dominate4"] = "#Charisma#Leadership"
    if dominate > 4:
        result["Dominate5"] = "#Charisma#Intimidation"

    flight = int(char.get("Flight", 0))
    # tODO
    # has no roll associated, remove or employ house-rules?
    if flight > 0:
        result["Flight1"] = one

    if flight > 1:
        result["Flight2"] = one

    if flight > 2:
        result["Flight3"] = one

    if flight > 3:
        result["Flight4"] = one

    if flight > 4:
        result["Flight5"] = one

    fortitude = int(char.get("Fortitude", 0))
    # tODO
    # grants extra dice for soaks, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if fortitude > 0:
        result["sta"] = "Stamina fortitude stabonus"
        result["Fortitude1"] = one

    if fortitude > 1:
        result["Fortitude2"] = one

    if fortitude > 2:
        result["Fortitude3"] = one

    if fortitude > 3:
        result["Fortitude4"] = one

    if fortitude > 4:
        result["Fortitude5"] = one

    melpominee = int(char.get("Melpominee", 0))
    if melpominee > 0:  # tODO
        result["Melpominee1"] = one
        # automatic, no roll
    if melpominee > 1:
        result["Melpominee2"] = "#Wits#Performance f7"  # spend 1 blood
    if melpominee > 2:
        result["Melpominee3"] = "#Charisma#Performance f7"
    if melpominee > 3:
        result["Melpominee4"] = "#Manipulation#Performance"
        # extended, resisted roll, diff depending on target #Willpower
        # resisted with willpower roll
        # (difficulty equal to the singer’s #Appearance#Performance)
    if melpominee > 4:
        result[
            "Melpominee5"
        ] = "#Stamina#Performance d1e1"  # spend 1 blood for every five targets beyond the first
    # tODO level 6 and 7

    mytherceria = int(char.get("Mytherceria", 0))
    if mytherceria > 0:  # tODO
        result["Mytherceria1"] = one
        # deliberate auto-success, no roll
    if mytherceria > 1:
        result["Mytherceria2"] = one
        # automatic, no roll
    if mytherceria > 2:
        result["Mytherceria3"] = "#Perception#Empathy"  # diff at gM discretion
    if mytherceria > 3:
        result["Mytherceria4"] = "#Intelligence#Larceny f7"
        # for inanimate object. use subject’s current willpower +2 otherwise
        # resist with #Wits#Investigation f8
    if mytherceria > 4:
        result[
            "Mytherceria5"
        ] = "#Manipulation#Occult"  # difficulty is the victim’s current willpower
        # tODO level 6,7 and 8

    necromancy = int(char.get("Necromancy", 0))
    if necromancy > 0:  # hausregeln!
        result["Necromancy1"] = "#Perception#Alertness f5"
    if necromancy > 1:
        result["Necromancy2"] = "#Manipulation#Occult"
    if necromancy > 2:
        result["Necromancy3"] = "#Occult"
    if necromancy > 3:
        result["Necromancy4"] = "#Willpower"
    if necromancy > 4:
        result["Necromancy5"] = one

    obeah = int(char.get("Obeah", 0))
    if obeah > 0:  # tODO
        result["Obeah1"] = "#Perception#Empathy f7"
    if obeah > 1:
        result[
            "Obeah2"
        ] = "#Willpower"  # for willing subject, #Willpower f8 otherwise, spend 1 blood in any case
    if obeah > 2:
        result["Obeah3"] = one
        # no roll, spend 1 blood, more for bigger wounds
    if obeah > 3:
        result["Obeah4"] = one
        # no roll, spend  two  willpower
        # resist in extended, resisted willpower roll battle,
        # first to be 3 successes in front of the other wins
    if obeah > 4:
        result["Obeah5"] = "#Intelligence#Empathy f8"  # spend  two  blood

    obfuscate = int(char.get("Obfuscate", 0))
    if obfuscate > 0:
        result["Obfuscate1"] = "#Dexterity#Stealth"
    if obfuscate > 1:
        result["Obfuscate2"] = "#Dexterity#Stealth"
    if obfuscate > 2:
        result["Obfuscate3"] = "#Manipulation#Performance f7"
    if obfuscate > 3:
        result["Obfuscate4"] = "#Charisma#Stealth"
    if obfuscate > 4:
        result["Obfuscate5"] = "#Stealth d1e1"

    obtenebration = int(char.get("Obtenebration", 0))
    if obtenebration > 0:
        result["Obtenebration1"] = one

    if obtenebration > 1:
        result["Obtenebration2"] = "#Manipulation#Occult f7"
    if obtenebration > 2:
        result["Obtenebration3"] = "#Manipulation#Occult f7"
    if obtenebration > 3:
        result["Obtenebration4"] = "#Manipulation#Courage f7"
    if obtenebration > 4:
        result["Obtenebration5"] = one

    potence = int(char.get("Potence", 0))
    # tODO
    # grants extra dice for strength rolls, not a roll by itself for levels 5 and lower,
    # optional powers _xor_ more dice at 6 and beyond
    if potence > 0:
        result["str"] = "Strength potence strbonus"
        result["Potence1"] = one

    if potence > 1:
        result["Potence2"] = one

    if potence > 2:
        result["Potence3"] = one

    if potence > 3:
        result["Potence4"] = one

    if potence > 4:
        result["Potence5"] = one

    # tODO levels 6,7 and 8

    presence = int(char.get("Presence", 0))
    if presence > 0:
        result["Presence1"] = "#Charisma#Performance f7"
    if presence > 1:
        result["Presence2"] = "#Charisma#Intimidation"
    if presence > 2:
        result["Presence3"] = "#Appearance#Empathy"
    if presence > 3:
        result["Presence4"] = "#Charisma#Subterfuge"
    if presence > 4:
        result["Presence5"] = one

    protean = int(char.get("Protean", 0))
    if protean > 0:
        result["Protean1"] = one
        # no roll
    if protean > 1:
        result["Protean2"] = one
        # spend 1 blood
    if protean > 2:
        result["Protean3"] = one
        # spend 1 blood
    if protean > 3:
        result["Protean4"] = one
        # spend 1 blood, up to 3 to transform faster
    if protean > 4:
        result["Protean5"] = one
        # spend 1 blood, up to 3 to transform faster
    # tODO levels up to 9

    quietus = int(char.get("Quietus", 0))
    if quietus > 0:
        result["Quietus1"] = one

    if quietus > 1:
        result["Quietus2"] = "#Willpower"
    if quietus > 2:
        result["Quietus3"] = "#Stamina"
    if quietus > 3:
        result["Quietus4"] = one

    if quietus > 4:
        result["Quietus5"] = "#Stamina#Athletics"
    # tODO levels up to 9

    serpentis = int(char.get("Serpentis", 0))
    if serpentis > 0:
        result["Serpentis1"] = "#Willpower f9"
    if serpentis > 1:
        result["Serpentis2"] = one
        # no roll
    if serpentis > 2:
        result["Serpentis3"] = one
        # spend one blood and one willpower
    if serpentis > 3:
        result["Serpentis4"] = one
        # spend 1 blood
    if serpentis > 4:
        result["Serpentis5"] = one
        # no roll

    temporis = int(char.get("Temporis", 0))
    if temporis > 0:
        result["Temporis1"] = one

    if temporis > 1:
        result["Temporis2"] = one

    if temporis > 2:
        result["Temporis3"] = one

    if temporis > 3:
        result["Temporis4"] = one

    if temporis > 4:
        result["Temporis5"] = one

    thaumaturgy = int(char.get("Thaumaturgy", 0))
    if thaumaturgy > 0:
        result["Thaumaturgy1"] = "#Willpower f4"
    if thaumaturgy > 1:
        result["Thaumaturgy2"] = "#Willpower f5"
    if thaumaturgy > 2:
        result["Thaumaturgy3"] = "#Willpower f6"
    if thaumaturgy > 3:
        result["Thaumaturgy4"] = "#Willpower f7"
    if thaumaturgy > 4:
        result["Thaumaturgy5"] = "#Willpower f8"

    vicissitude = int(char.get("Vicissitude", 0))
    if vicissitude > 0:
        result[
            "Vicissitude1"
        ] = "#Intelligence#Medicine"  # spend one blood point for each body part to be changed
        # #Perception#Medicine f8 if trying to imitate someones face or voice
    if vicissitude > 1:
        result[
            "Vicissitude2"
        ] = "#Dexterity#Medicine"  # spend 1 blood, variable difficulty
    if vicissitude > 2:
        result[
            "Vicissitude3"
        ] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
    if vicissitude > 3:
        result["Vicissitude4"] = one
        # no roll, spend two blood points
    if vicissitude > 4:
        result["Vicissitude5"] = one
        # roll system insufficient, this is all about blood
    # tODO up to level 9

    visceratica = int(char.get("Visceratica", 0))
    if visceratica > 0:
        result["Visceratica1"] = one  # spend one blood, +5 stealth for scene
    if visceratica > 1:
        result["Visceratica2"] = one  # spend 1 blood, variable difficulty
    if visceratica > 2:
        result[
            "Visceratica3"
        ] = "#Strength#Medicine"  # spend 1 blood, variable difficulty
    if visceratica > 3:
        result["Visceratica4"] = one  # no roll, spend two blood points
    if visceratica > 4:
        result[
            "Visceratica5"
        ] = one  # roll system insufficient, this is all about blood

    return result
