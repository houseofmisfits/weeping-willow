from houseofmisfits.weeping_willow import WeepingWillowClient
import yaml


if __name__ == '__main__':
    client = WeepingWillowClient('botconfig.yml')
    client.run()
