import random
import math


def iterative_speed(thrust, amount, anchor, mass, dynamics) -> dict:
    dt = 0.1
    speed = 0.0
    mech_total_mass = mass * amount
    if mech_total_mass <= 0:
        return {"topspeed": 0.0, "duration": 0.0, "time90": 0.0}

    thrust_force = thrust * amount
    friction_force = anchor * mech_total_mass
    net_force = thrust_force - friction_force

    if net_force <= 0:
        return {"topspeed": 0.0, "duration": 0.0, "time90": 0.0}

    if dynamics == 0:
        v_max = net_force ** (1 / 3)
    else:
        v_max = math.sqrt(net_force * dynamics / 10)

    accel = 1.0
    seconds = 0.0
    time90 = 0.0
    while accel > 0.001 and seconds < 1000:
        if dynamics == 0:
            drag_force = speed**3
        else:
            drag_force = speed**2 / (dynamics / 10)

        accel = (thrust_force - friction_force - drag_force) / (mech_total_mass * 10)
        speed += accel * dt
        seconds += dt
        if time90 == 0 and speed >= 0.9 * v_max:
            time90 = seconds

    return {"topspeed": speed * 3.6, "duration": seconds, "time90": time90}


def rule_of_thumb_speed(thrust, amount, anchor, mass, dynamics) -> dict:
    mech_total_mass = mass * amount
    net_force = (thrust * amount) - (anchor * mech_total_mass)

    if net_force <= 0:
        return {"topspeed": 0.0, "duration": 0.0, "time90": 0.0}

    if dynamics == 0:
        v_max = net_force ** (1 / 3)
        tau = (mech_total_mass * 10) * v_max / net_force
        time90 = 1.0 * tau  # Cubic drag reaches 90% faster than quadratic
    else:
        v_max = math.sqrt(net_force * dynamics / 10)
        tau = (mech_total_mass * 10) * v_max / net_force
        time90 = 1.5 * tau

    return {"topspeed": v_max * 3.6, "duration": 5 * tau, "time90": time90}


def test_formulas():
    passed_speed = 0
    passed_time90 = 0
    total = 100

    header = (
        f"{'Thrust':>6} | {'Mass':>6} | {'Dyn':>4} | {'Actual S':>8} | "
        f"{'Rule S':>8} | {'Act T90':>7} | {'Rule T90':>7} | {'T Diff %':>6}"
    )
    print(header)
    print("-" * len(header))

    for _ in range(total):
        thrust = random.uniform(10, 1000)
        amount = random.randint(1, 20)
        anchor = random.uniform(0.01, 2.0)
        mass = random.uniform(1, 10)
        dynamics = random.choice([0, 1, 2, 5, 10, 20, 50])

        actual = iterative_speed(thrust, amount, anchor, mass, dynamics)
        rule = rule_of_thumb_speed(thrust, amount, anchor, mass, dynamics)

        if actual["topspeed"] == 0:
            if rule["topspeed"] == 0:
                passed_speed += 1
                passed_time90 += 1
            continue

        diff_s = abs(actual["topspeed"] - rule["topspeed"]) / actual["topspeed"]
        diff_t = (
            abs(actual["time90"] - rule["time90"]) / actual["time90"]
            if actual["time90"] > 0
            else 0
        )

        if diff_s <= 0.10:
            passed_speed += 1
        if diff_t <= 0.15:  # Time 90% should be within 15%
            passed_time90 += 1

        if _ < 10:  # Print first 10
            line = (
                f"{thrust:6.1f} | {mass * amount:6.1f} | {dynamics:4} | "
                f"{actual['topspeed']:8.1f} | {rule['topspeed']:8.1f} | "
                f"{actual['time90']:7.1f} | {rule['time90']:8.1f} | {diff_t * 100:6.1f}%"
            )
            print(line)

    print("-" * len(header))
    print(f"Speed Passed: {passed_speed}/{total} (within 10%)")
    print(f"Time 90% Passed: {passed_time90}/{total} (within 15%)")


if __name__ == "__main__":
    test_formulas()
