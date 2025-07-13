---
outgoing links: []
tags:
- mech
title: testmecha
---

# Description

# Systems

## Movement

|        | Energy | Heat | Thrust | Anchor | Dynamics | Mass | Amount |
|--------|--------|------|--------|--------|----------|------|--------|
| Wheels | 100.0  | 5    | 400.0  | 0.5    | 5.0      | 2.0  | 10.0   |
| Rails  | 100.0  | 3    | 200.0  | 0.001  | 1000.0   | 3.0  | 10.0   |

## Energy

|                     | Energy | Mass | Amount | Enabled |
|---------------------|--------|------|--------|---------|
| baseloadreactor     | 50.0   | 5.0  | 1.0    |         |
| peakload stage 1    | 20.0   | 5.0  | 1.0    |         |
| peakload stage 2    | 20.0   | 5.0  | 1.0    |         |
| backup generator    | 15.0   | 5.0  | 1.0    |         |
| emergency generator | 10.0   | 5.0  | 1.0    |         |

## Heat

|         | Capacity | Passive | Active | Flux | Current |
|---------|----------|---------|--------|------|---------|
| Vent    | 100.0    | 10%     | 2      | 5.0  | 0.0     |
| Coolant | 50.0     | 0       | 10     | 25.0 | 0.0     |
| Sink    | 400.0    | 1%      | 0.01   | 0.0  | 0.0     |

## Offensive

|         | Energy | Mass | Amount |
|---------|--------|------|--------|
| AutoGun | 30.0   | 7.0  | 1.0    |

## Defensive

|            | Energy | Mass | Amount |
|------------|--------|------|--------|
| Junk Armor | 0.0    | 5.0  | 5.0    |

## Support

|                | Energy | Mass | Amount |
|----------------|--------|------|--------|
| Coffee machine | 30.0   | 1.0  | 1.0    |

## Seal

|                            | Level |
|----------------------------|-------|
| External Experimental Seal | 25.0  |

# Loadouts

## Default
[0], Wheels, [10.0], Rails, [15.0], Vent, Coolant, Sink, Junk Armor, [20.0], AutoGun, [25.0], Coffee machine, [30.0]
