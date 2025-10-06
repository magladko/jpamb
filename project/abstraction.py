from dataclasses import dataclass
from typing import TypeAlias, Literal

Sign : TypeAlias = Literal["+"] | Literal["-"] | Literal["0"]

@dataclass
class SignSet:
    signs : set[Sign]

    @classmethod
    def abstract(cls, items : set[int]):
        signset = set()
        if 0 in items:
            signset.add("0")
        if any([x for x in items if x > 0]):
            signset.add("+")
        if any([x for x in items if x < 0]):
            signset.add("-")
        return cls(signset)

    def compare_signs(self, s1: Sign, s2: Sign) -> set[Sign]:
        if s1 == s2:
            return {s1}
        if s1 == "0" and s2 != "0":
            return {s1}
        if s1 != "0" and s2 == "0":
            return {s2}
        return {"+", "-", "0"}

    def __contains__(self, member : int):
        if (member == 0 and "0" in self.signs):
            return True
        if (member > 0 and "+" in self.signs):
            return True
        if (member < 0 and "-" in self.signs):
            return True
        return False

    def __add__(self, other):
        assert isinstance(other, SignSet)
        new_signlist = SignSet(set())
        for ss in self.signs:
            for os in other.signs:
                new_signlist.signs.update(self.compare_signs(ss, os))
        return new_signlist

    def __le__(self, other):
        assert isinstance(other, SignSet)
        return self.signs <= other.signs

    def __eq__(self, other):
        assert isinstance(other, SignSet)
        return self.signs == other.signs
