"""
Setup configuration for FazzTV broadcasting system.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="fazztv",
    version="1.0.0",
    author="FazzTV Development Team",
    description="Automated Video Broadcasting System with RTMP support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/thefazzer/fazztv",
    packages=find_packages(exclude=["tests", "tests.*"]),
    python_requires=">=3.8",
    install_requires=[
        "yt-dlp>=2023.1.0",
        "loguru>=0.7.0",
        "requests>=2.28.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "fazztv=fazztv.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="video broadcasting rtmp streaming youtube automation",
    package_data={
        "fazztv": ["data/*.json", "data/*.md"],
    },
)