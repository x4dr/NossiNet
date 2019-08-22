from math import ceil
import requests

import plotly
from plotly.offline import offline

balanced_modifiers = [0.17202107691263938, 0.1613333634862842, 0.14626744159750332, 0.12806712046857685,
                      0.10685904249304598, 0.08603089169813881, 0.06636966010086162, 0.04910106515298854,
                      0.033171261222551394, 0.050770030982156995]

one_sided_modifiers = [0.04256588711941915, 0.05309579204942035, 0.06453828874002167, 0.07635936058405873,
                       0.08557553451803121, 0.09267068474467488, 0.09599011191784669, 0.09552629467688234,
                       0.09044436198804605, 0.3032336836615989]


def modify_dmg(modifiers, dmgstring, type, armor):
    dmg = [int(x) for x in dmgstring.split("|") if x.strip()]
    total = 0
    effectivedmg = []
    for d in dmg:
        if type == "Stechen":
            effectivedmg.append(0 if d <= armor else d)
        elif type == "Schlagen":
            e = d - int(armor / 2)
            effectivedmg.append(e if e > 0 else 0)
        elif type == "Schneiden":
            e = d - armor
            effectivedmg.append(e + ceil(e / 5) * 3 if e > 0 else 0)
        else:
            e = d - armor
            effectivedmg.append(e if e > 0 else 0)

    for i, d in enumerate(effectivedmg):
        total += d * modifiers[i]
    return total


r = requests.get("nosferatu.vampir.es/wiki/weapons")
r.content

dmgraw = """ 
###Kurzschwert
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |   
| [Stechen](damage#p-stechen)      | 1 | 2 | 3 | 4 | 4 | 5 | 5 | 6 | 6 | 7 |   
| [Schneiden](weapons#c-schneiden) | 1 | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 7 |   
| [Schlagen](damage#b-stumpf)      | 1 | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 7 |   

###Langschwert
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 4 | 5 | 6 | 7 | 7 | 8 | 9 | 10| 11 | 12 |   
| [Stechen](damage#p-stechen)      | 2 | 3 | 4 | 4 | 5 | 6 | 6 | 7 | 7 | 8 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 | 7 | 8 |   
| [Schlagen](damage#b-stumpf)      | 2 | 3 | 3 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |   

###Dolch
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 1 | 2 | 3 | 4 | 5 | 5 | 8 | 10 | 12 | 14 |   
| [Stechen](damage#p-stechen)      | 1 | 2 | 3 | 4 | 4 | 5 | 5 | 8 | 11 | 14 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 8  |   
| [Schlagen](damage#b-stumpf)      | 1 | 1 | 1 | 2 | 2 | 2 | 3 | 3 | 3 | 10 |  

###Hammer
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  
| [Stechen](damage#p-stechen)      | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Schneiden](weapons#c-schneiden) | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| [Schlagen](damage#b-stumpf)      | 4 | 4 | 5 | 5 | 6 | 7 | 8 | 10 | 12 | 15 | 

###Axt
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 3 | 3 | 4 | 5 | 6 | 8 | 10 | 12 | 14 | 16 |   
| [Stechen](damage#p-stechen)      | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Schneiden](weapons#c-schneiden) | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 8 | 10 |
| [Schlagen](damage#b-stumpf)      | 2 | 3 | 4 | 5 | 6 | 6 | 6 | 6 | 6 | 6 | 

###Säbel
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |   
| [Stechen](damage#p-stechen)      | 1 | 1 | 2 | 2 | 3 | 3 | 4 | 5 | 6 | 7 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |    
| [Schlagen](damage#b-stumpf)      | 2 | 2 | 2 | 3 | 3 | 4 | 4 | 5 | 5 | 6 |  

###Kurzspeer
| Wert                             | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |   
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| [Hauen](damage#h-hauen)          | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |   
| [Stechen](damage#p-stechen)      | 2 | 3 | 4 | 5 | 5 | 6 | 7 | 9 | 12 | 15 |   
| [Schneiden](weapons#c-schneiden) | 2 | 3 | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5  |   
| [Schlagen](damage#b-stumpf)      | 2 | 3 | 4 | 4 | 4 | 5 | 5 | 5 | 6 | 6 |  """

armormax = 14

weapons = {}
for dmgsect in dmgraw.split("###"):
    if not dmgsect.strip():
        continue
    weapon = dmgsect[:dmgsect.find("\n")].strip()
    weapons[weapon] = {}
    for dmgline in dmgsect.split("\n"):
        if "Wert" in dmgline or "---" in dmgline or len(dmgline) < 50:
            continue
        dmgtype = dmgline[dmgline.find("[") + 1:dmgline.find("]")].strip()
        weapons[weapon][dmgtype] = dmgline[35:]
weaponnames = list(weapons.keys())
types = list(weapons[weaponnames[0]].keys())

damage = []
for i in range(armormax):
    damage.append({})
    for w in weapons.keys():
        damage[-1][w] = {}
        for d in weapons[w].keys():
            damage[-1][w][d] = modify_dmg(balanced_modifiers, weapons[w][d], d, i)

traces = []
for i in range(armormax):
    traces.append([])
    for t in types:
        traces[-1].append(dict(
            type="bar",
            x=weaponnames,
            y=[damage[i][x][t] for x in weaponnames],
            name=t
        ))

frames = [plotly.graph_objs.Frame(name="Frame" + str(i), data=traces[i]) for i in range(0, armormax)]
slider = {
    'args': [
        'transition', {
            'duration': 400,
            'easing': 'cubic-in-out'
        }
    ],
    'initialValue': '0',
    'plotlycommand': 'animate',
    'values': [str(x) for x in range(armormax)],
    'visible': True
}
sliders_dict = {
    'active': 0,
    'yanchor': 'top',
    'xanchor': 'left',
    'currentvalue': {
        'font': {'size': 15},
        'prefix': 'Armor:',
        'visible': True,
        'xanchor': 'right'
    },
    'transition': {'duration': 200, 'easing': 'cubic-in-out'},
    'pad': {'b': 1, 't': 5},
    'len': 0.9,
    'x': 0,
    'y': 0,
    'steps': []
}
for i in range(armormax):
    slider_step = dict(method='animate',
                       args=[["Frame" + str(i)],
                             dict(mode='immediate',
                                  frame=dict(duration=200, redraw=True),
                                  transition=dict(duration=100)
                                  )
                             ],
                       label=str(i)
                       )
    sliders_dict['steps'].append(slider_step)

layout = dict(xaxis=dict(zeroline=False, autorange=True),
              yaxis=dict(autorange=True, zeroline=False),
              title='Compare', hovermode='closest',
              sliders=[slider]
              )

data = traces[0]

figure1 = dict(data=data, layout=layout, frames=frames)

figure1['layout']['sliders'] = [sliders_dict]

offline.plot(figure1, image_filename="weapontypes")
