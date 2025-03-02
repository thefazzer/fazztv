from setuptools import setup, find_packages

setup(
    name="fazztv",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "yt-dlp",
        "openai",
        "loguru",
    ],
    entry_points={
        'console_scripts': [
            'fazztv=fazztv.main:main',
        ],
    },
)