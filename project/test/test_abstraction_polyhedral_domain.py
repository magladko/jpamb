from project.abstractions.novel_domains import (
    PolyhedralDomain,
)


def test_polyhedral_domain_bounds_and_ops() -> None:
    box_a = PolyhedralDomain.abstract({(0.0, 1.0), (2.0, 3.0)})
    box_b = PolyhedralDomain.abstract({(1.0, 0.0), (4.0, 2.0)})
    assert (1.0, 1.0) in box_a
    summed = box_a + box_b
    assert (3.0, 3.0) in summed
    intersection = box_a & box_b
    assert intersection.bounds == [(1.0, 2.0), (1.0, 2.0)]
    joined = box_a | box_b
    assert joined.bounds == [(0.0, 4.0), (0.0, 3.0)]
