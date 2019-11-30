from houseofmisfits.weeping_willow import WeepingWillowClient


if __name__ == '__main__':
    client = WeepingWillowClient('/run/secrets/botconfig.yml')
    client.run()
