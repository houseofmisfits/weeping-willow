from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read()

setup(
    name='Weeping Willow',
    description='House of Misfits custom bot',
    version='0.0.1',
    packages=['houseofmisfits.weeping_willow'],
    install_requires=requirements,
    license='Proprietary',
    classifiers=[
        'License :: Other/Proprietary License'
    ]
)
