import asyncio
import logging

import asyncpg

logger = logging.getLogger(__name__)

version_functions = []


def upgrade_database(client):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(upgrade_database_async(client))


async def upgrade_database_async(client):
    logger.debug("Checking for database updates")
    current_version = await _get_current_version(client)
    for from_version, to_version, func in version_functions:
        if current_version == from_version:
            logger.info("Upgrading from {} to {}".format(from_version, to_version))
            await func(client)
            await _set_version(client, to_version)
            current_version = to_version

    logger.debug("Database is up to date")


async def _get_current_version(client):
    conn = await client.data_connection.pool.acquire()
    try:
        result = await conn.fetchrow('SELECT version FROM _version')
        return result['version']
    except asyncpg.UndefinedTableError:
        return '0.0.0'
    finally:
        await conn.close()


async def _set_version(client, version):
    async with client.data_connection.pool.acquire() as conn:
        await conn.execute('UPDATE _version SET version = $1', version)


def upgrade(from_version, to_version):
    def decorate(func):
        version_functions.append((from_version, to_version, func))
        return func

    return decorate


@upgrade(from_version='0.0.0', to_version='0.0.1')
async def initialize_database(client):
    logger.info("Creating _version table")
    async with client.data_connection.pool.acquire() as conn, conn.transaction():
        await conn.execute("""
            CREATE TABLE _version (
                version VARCHAR(15)
            ) ;
            
            INSERT INTO _version VALUES ('0.0.0') ;
        """)


@upgrade(from_version='0.0.1', to_version='0.0.2')
@upgrade(from_version='0.0.2-dev', to_version='0.0.2')
async def make_module_commands(client):
    async with client.data_connection.pool.acquire() as conn, conn.transaction():
        logger.info("Moving event config keys to event tables")
        result = await conn.fetch("""
            SELECT config_key, config_val
            FROM bot_config
            WHERE config_key LIKE 'participant_channel%' ;
        """)

        event_days = {row['config_key']: row['config_val'] for row in result}

        await conn.execute("""
            CREATE TABLE event_channels (
                day_of_week int2 NOT NULL,
                channel_id bigint,
                CONSTRAINT day_of_week_pkey PRIMARY KEY (day_of_week)
            );
        """)

        config_keys = ['participant_channel_mon', 'participant_channel_tue',
                       'participant_channel_wed', 'participant_channel_thu', 'participant_channel_fri',
                       'participant_channel_sat', 'participant_channel_sun']

        for i in range(7):
            config_key = config_keys[i]
            channel_id = int(event_days[config_key]) if config_key in event_days else None
            await conn.execute("""
                INSERT INTO event_channels
                VALUES ($1, $2) ;
            """, i, channel_id)

        await conn.execute("""
            DELETE FROM bot_config
            WHERE config_key LIKE 'participant_channel%' ;
        """)

        await conn.execute("""
                CREATE TABLE event_participants (
                    participation_dt DATE NOT NULL,
                    member_id bigint,
                    message_id bigint,
                    CONSTRAINT event_participation_pkey PRIMARY KEY (participation_dt, member_id)
                );
            """)
