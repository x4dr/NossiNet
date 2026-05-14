---
outgoing links: []
tags:
- mech
title: testmecha
---
# Description

# Systems

## Movement
|        | Energy | Heat | Thrust | Anchor | Dynamics | Mass | Amount | Enabled |
|------|------|----|------|------|--------|----|------|-------|
| Wheels | 20     | 5    | 400    | 0.5    | 5        | 2    | 1      | [ ]     |
| Rails  | 15     | 3    | 200    | 0.001  | 1000     | 3    | 1      | [ ]     |

## Energy
|                     | Energy | Mass | Amount | Heat | Shutoff | Enabled |
|-------------------|------|----|------|----|-------|-------|
| baseloadreactor     | 50     | 5    | 1      | 10   | 0       | [ ]     |
| peakload stage 1    | 20     | 5    | 1      | 5    | 0       | [ ]     |
| peakload stage 2    | 20     | 5    | 1      | 5    | 0       | [ ]     |
| backup generator    | 15     | 5    | 1      | 2    | 0       | [ ]     |
| emergency generator | 10     | 5    | 1      | 1    | 0       | [ ]     |

## Heat
|         | Energy | Mass | Amount | Heat | Capacity | Passive | Active | Flux | Current | Enabled |
|-------|------|----|------|----|--------|-------|------|----|-------|-------|
| Vent    | 5      | 1    | 1      | 0    | 100      | 10%     | 2      | 5    | 0       | [ ]     |
| Coolant | 0      | 1    | 1      | 0    | 50       | 0       | 10%    | 10   | 0       | [ ]     |
| Sink    | 5      | 5    | 1      | 0    | 400      | 1%      | 0.01   | 1    | 0       | [ ]     |

## Offensive
|         | Energy | Mass | Heat | Amount | Enabled |
|-------|------|----|----|------|-------|
| AutoGun | 30     | 7    | 0    | 1      | [ ]     |

## Defensive
|            | Energy | Mass | Heat | Amount | Enabled |
|----------|------|----|----|------|-------|
| Junk Armor | 0      | 5    | 0    | 5      | [ ]     |

## Support
|                | Energy | Mass | Heat | Amount | Enabled |
|--------------|------|----|----|------|-------|
| Coffee machine | 30     | 1    | 0    | 1      | [ ]     |

## Seal
|                            | Level |
|--------------------------|-----|
| External Experimental Seal | 25    |

# Sectors

# Loadouts

## Default
[0], baseloadreactor, [10], Wheels, [15], Rails, [20], Vent, Coolant, Sink, Junk Armor, [25], AutoGun, [30], Coffee machine, [35]

## FuelConserving
[0], baseloadreactor, [10], Wheels, [15], Vent, Coolant, Junk Armor, [20]

## Cool
[0], baseloadreactor, [10], Vent, Coolant, [15], Sink, [20]
