from typing import AsyncIterable

from houseofmisfits.weeping_willow.triggers import Trigger


class Module:
    async def get_triggers(self) -> AsyncIterable[Trigger]:
        raise NotImplementedError()
