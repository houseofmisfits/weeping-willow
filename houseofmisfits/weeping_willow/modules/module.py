from typing import List

from houseofmisfits.weeping_willow.triggers import Trigger


class Module:
    def get_triggers(self) -> List[Trigger]:
        raise NotImplementedError()
