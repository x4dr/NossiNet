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
| Wheels | 100    | 5    | 400    | 0.5    | 5        | 2    | 10     |         |
| Rails  | 100    | 3    | 200    | 0.001  | 1000     | 3    | 10     |         |

## Energy
|                     | Energy | Mass | Amount | Enabled |
|-------------------|------|----|------|-------|
| baseloadreactor     | 50     | 5    | 1      |         |
| peakload stage 1    | 20     | 5    | 1      |         |
| peakload stage 2    | 20     | 5    | 1      |         |
| backup generator    | 15     | 5    | 1      |         |
| emergency generator | 10     | 5    | 1      |         |

## Heat
|         | Energy | Mass | Amount | Heat | Capacity | Passive | Active | Flux | Current | Enabled |
|-------|------|----|------|----|--------|-------|------|----|-------|-------|
| Vent    | 0      | 0    | 0      | 0    | 100      | 10%     | 2      | 5    | 0       |         |
| Coolant | 0      | 0    | 0      | 0    | 50       | 0       | 10     | 25   | 0       |         |
| Sink    | 0      | 0    | 0      | 0    | 400      | 1%      | 0.01   | 0    | 0       |         |

## Offensive
|         | Energy | Mass | Heat | Amount | Enabled |
|-------|------|----|----|------|-------|
| AutoGun | 30     | 7    | 0    | 1      |         |

## Defensive
|            | Energy | Mass | Heat | Amount | Enabled |
|----------|------|----|----|------|-------|
| Junk Armor | 0      | 5    | 0    | 5      |         |

## Support
|                | Energy | Mass | Heat | Amount | Enabled |
|--------------|------|----|----|------|-------|
| Coffee machine | 30     | 1    | 0    | 1      |         |

## Seal
|                            | Level |
|--------------------------|-----|
| External Experimental Seal | 25    |

# Loadouts

## Default
[0], Wheels, [10], Rails, [15], Vent, Coolant, Sink, Junk Armor, [20], AutoGun, [25], Coffee machine, [30]
