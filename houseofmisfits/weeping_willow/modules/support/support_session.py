from enum import Enum

import asyncpg

import logging

from houseofmisfits.weeping_willow.modules.support import SupportChannel

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SupportSession:
    def __init__(self, support_channel):
        self.channel = support_channel
        self.client = support_channel.client
        self.user = support_channel.user
        self.brand_new = None
        self.session_id = None

    @classmethod
    async def for_user(cls, user, client):
        support_channel = await SupportChannel.for_user(user, client)
        self = await SupportSession.in_channel(support_channel)
        return self

    @classmethod
    async def in_channel(cls, channel):
        self = SupportSession(channel)
        await self._retrieve_session_info()
        return self

    async def _retrieve_session_info(self):
        session_info = await self._get_existing_session(self.user.id)
        if session_info is None:
            logger.debug("Making session for user {}".format(self.user.name))
            await self._make_new_session(self.user.id, self.channel.id)
            session_info = await self._get_existing_session(self.user.id)
            self.brand_new = True
        else:
            self.brand_new = False
        self.session_id = session_info['session_id']
        logger.debug("Session ID for user [{}]: {}".format(self.user.name, self.session_id))

    async def _get_existing_session(self, user_id):
        async with self.client.acquire_data_connection() as conn:
            try:
                return await conn.fetchrow(
                    "SELECT * FROM support_session"
                    "  WHERE member_id = $1 "
                    "  AND session_status NOT IN ('Closed', 'Cancelled')"
                    "  AND session_dt > CURRENT_DATE - 2",
                    str(user_id)
                )
            except asyncpg.UndefinedTableError:
                await self._build_support_session_table(conn)
                return None

    async def _make_new_session(self, user_id, channel_id):
        async with self.client.acquire_data_connection() as conn:
            await conn.execute(
                """
                    INSERT INTO support_session
                    (member_id, channel_id, session_status)
                    VALUES ($1, $2, $3)
                """,
                str(user_id),
                str(channel_id),
                SupportSession.Status.NEW.value
            )

    @staticmethod
    async def _build_support_session_table(conn):
        logger.warning("The support session table doesn't exist! Creating it now.")
        await conn.execute("""
            CREATE TABLE support_session (
                session_id SERIAL PRIMARY KEY,
                member_id VARCHAR(20) NOT NULL,
                session_dt DATE DEFAULT CURRENT_DATE,
                session_create_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_start_ts TIMESTAMP,
                session_end_ts TIMESTAMP,
                channel_id VARCHAR(20),
                session_status VARCHAR(15)
            )
        """)
        await conn.execute("CREATE INDEX ix_session_dt ON support_session (session_dt)")

    async def close(self):
        await self.set_status(self.Status.CLOSED)
        await self.channel.archive()
        await self.channel.send('This session is now closed. Insert helpful message here about being able to read messages')

    async def create_timestamp(self):
        return await self._get_value('session_create_ts')

    async def start_timestamp(self):
        return await self._get_value('session_start_ts')

    async def reset_start_timestamp(self):
        await self._set_to_current_timestamp('session_start_ts')

    async def end_timestamp(self):
        return await self._get_value('session_end_ts')

    async def reset_end_timestamp(self):
        await self._set_to_current_timestamp('session_end_ts')

    async def status(self):
        status_str = await self._get_value('session_status')
        return self.Status[status_str]

    async def set_status(self, status: 'SupportSession.Status'):
        await self._set_row_value('session_status', status.value)

    async def _get_value(self, field):
        async with self.client.acquire_data_connection() as conn:
            row = await conn.fetchrow(
                'SELECT {} FROM support_session WHERE session_id = $1'.format(field), self.session_id
            )
            return row[field]

    async def _set_to_current_timestamp(self, field):
        async with self.client.acquire_data_connection() as conn:
            await conn.execute("UPDATE support_session "
                               "SET {} = CURRENT_TIMESTAMP "
                               "WHERE session_id = $1".format(field), self.session_id)

    async def _set_row_value(self, field, value):
        async with self.client.acquire_data_connection() as conn:
            await conn.execute("UPDATE support_session "
                               "SET {} = $2 "
                               "WHERE session_id = $1".format(field), self.session_id, value)

    class Status(Enum):
        NEW = 'New'
        STARTED = 'Started'
        CLOSED = 'Closed'
        CANCELLED = 'Cancelled'




