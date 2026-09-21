"""Small finite checks for the metric-path proposal in email.pdf.

The diagrams below are genuine singleton persistence diagrams
{(s, s + M)}.  For fixed M and shifts smaller than M/2, bottleneck distance
between two such diagrams equals the absolute shift in s.  Thus the examples
are persistence-diagram examples, rather than an unrelated Euclidean proxy.
"""

from math import acos, hypot, pi


def comparison_angle(xm, x0, xp):
    a = hypot(x0[0] - xm[0], x0[1] - xm[1])
    b = hypot(xp[0] - x0[0], xp[1] - x0[1])
    c = hypot(xp[0] - xm[0], xp[1] - xm[1])
    if a == 0 or b == 0:
        return None
    z = (a * a + b * b - c * c) / (2 * a * b)
    return acos(max(-1.0, min(1.0, z)))


def singleton_bottleneck(s, t, lifespan=10.0):
    """Bottleneck distance for two equal-lifespan singleton diagrams.

    For the shifts used here, matching the off-diagonal points is optimal,
    because the diagonal cost is lifespan/2.
    """
    assert abs(s - t) < lifespan / 2
    return abs(s - t)


def finite_stability_checks():
    """Check the triangle-inequality error bounds on a finite example."""
    original = [0.0, 1.0, 2.0, 1.0, 0.0]
    perturb = [0.001, -0.002, 0.0005, -0.001, 0.002]
    eps = [abs(x) for x in perturb]
    shifted = [x + e for x, e in zip(original, perturb)]
    dt = 0.25
    speed = [singleton_bottleneck(original[i], original[i + 1]) / dt
             for i in range(4)]
    shifted_speed = [singleton_bottleneck(shifted[i], shifted[i + 1]) / dt
                     for i in range(4)]
    speed_errors = [abs(x - y) for x, y in zip(speed, shifted_speed)]
    speed_bounds = [(eps[i] + eps[i + 1]) / dt for i in range(4)]
    assert all(e <= b + 1e-12 for e, b in zip(speed_errors, speed_bounds))

    length = sum(singleton_bottleneck(original[i], original[i + 1])
                 for i in range(4))
    shifted_length = sum(singleton_bottleneck(shifted[i], shifted[i + 1])
                         for i in range(4))
    length_bound = sum(eps[i] + eps[i + 1] for i in range(4))
    assert abs(length - shifted_length) <= length_bound + 1e-12
    displacement = singleton_bottleneck(original[0], original[-1])
    shifted_displacement = singleton_bottleneck(shifted[0], shifted[-1])
    assert abs(displacement - shifted_displacement) <= eps[0] + eps[-1] + 1e-12
    print("finite speed errors", speed_errors)
    print("finite speed bounds", speed_bounds)
    print("finite length error/bound", abs(length - shifted_length), length_bound)
    print("finite displacement error/bound", abs(displacement - shifted_displacement),
          eps[0] + eps[-1])


def main():
    M = 10.0
    # Two paths of singleton persistence diagrams. Their consecutive
    # bottleneck distances, L, R, and scalar speed sequence are identical,
    # but their intermediate order differs.
    path_a = [0.0, 1.0, 2.0, 1.0, 0.0]
    path_b = [0.0, 1.0, 0.0, -1.0, 0.0]
    increments_a = [singleton_bottleneck(path_a[i], path_a[i + 1], M)
                    for i in range(4)]
    increments_b = [singleton_bottleneck(path_b[i], path_b[i + 1], M)
                    for i in range(4)]
    print("singleton PD points are (birth, death)=(s,s+M), M", M)
    print("same consecutive bottleneck distances", increments_a, increments_b)
    print("same L and R", sum(increments_a), abs(path_a[-1] - path_a[0]),
          sum(increments_b), abs(path_b[-1] - path_b[0]))
    angles_a = [comparison_angle((path_a[i], path_a[i] + M),
                                 (path_a[i + 1], path_a[i + 1] + M),
                                 (path_a[i + 2], path_a[i + 2] + M))
                for i in range(3)]
    angles_b = [comparison_angle((path_b[i], path_b[i] + M),
                                 (path_b[i + 1], path_b[i + 1] + M),
                                 (path_b[i + 2], path_b[i + 2] + M))
                for i in range(3)]
    print("comparison angles for paths A/B", angles_a, angles_b)

    # Same direction, equally spaced: a=b=1, c=2.
    straight = comparison_angle((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))
    print("straight comparison angle", straight, "pi", pi)

    # A perturbation of size 2 eps changes the comparison angle by pi when
    # the last increment is eps.  This is the small-step instability of the
    # angle, even though the first increment remains length one.
    eps = 1.0e-8
    before = comparison_angle((0.0, 0.0), (1.0, 0.0), (1.0 + eps, 0.0))
    after = comparison_angle((0.0, 0.0), (1.0, 0.0), (1.0 - eps, 0.0))
    perturbation = abs((1.0 + eps) - (1.0 - eps))
    print("angle before", before, "angle after", after)
    print("endpoint perturbation", perturbation, "angle jump", abs(before - after))

    # A zero increment makes the proposed denominator 2ab vanish.
    print("zero-increment angle", comparison_angle((0.0, 0.0), (1.0, 0.0), (1.0, 0.0)))
    finite_stability_checks()


if __name__ == "__main__":
    main()
