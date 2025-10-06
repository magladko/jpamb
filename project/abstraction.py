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

    def __contains__(self, member : int):
        if (member == 0 and "0" in self.signs):
            return True
        if (member > 0 and "+" in self.signs):
            return True
        if (member < 0 and "-" in self.signs):
            return True
        return False
