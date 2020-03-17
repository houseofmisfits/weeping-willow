from houseofmisfits.weeping_willow import WeepingWillowClient

import logging

if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    client = WeepingWillowClient()
    client.run()
