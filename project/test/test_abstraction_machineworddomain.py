from project.abstractions.machine_word import (
    MachineWordDomain,
)


def test_machine_word_arithmetic_wraps_and_tracks() -> None:
    mask = (1 << MachineWordDomain.WIDTH) - 1
    a = MachineWordDomain.abstract({1})
    b = MachineWordDomain.abstract({mask})
    wrapped = a + b
    assert 0 in wrapped
    assert wrapped <= MachineWordDomain.top()


def test_machine_word_equality_partitioning() -> None:
    value5 = 5
    value7 = 7

    a = MachineWordDomain.abstract({value5})
    b = MachineWordDomain.abstract({value5, value7})
    result = a.compare("eq", b)

    # split assertion into two
    assert True in result
    assert False in result

    true_left, true_right = result[True]
    false_left, false_right = result[False]

    assert value5 in true_left
    assert value5 in true_right
    assert value7 in false_right
    assert value5 in false_left
