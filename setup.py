from setuptools import setup, find_packages

setup(
    name='bot',
    description='Discord bot for NW company management',
    packages=find_packages(),
    entry_points="""
        [console_scripts]
        bot = src:start
    """,
)