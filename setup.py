from setuptools import setup, find_packages
import os

# Read version from VERSION file
with open('VERSION', 'r') as f:
    version = f.read().strip()

# Read long description from README.md
with open('README.md', 'r') as f:
    long_description = f.read()

setup(
    name="r2-sync",
    version=version,
    author="Frederike Reppekus",
    author_email="r2reppekus@gmail.com",
    description="Calendar synchronization tool for Nextcloud, Kerio, and Google Calendar",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Freddie-GER/R2-Sync",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "google-api-python-client>=2.70.0",
        "google-auth>=2.3.0",
        "google-auth-oauthlib>=0.4.6",
        "caldav>=0.9.0",
        "python-dotenv>=0.21.0",
        "requests==2.31.0",
        "icalendar==5.0.11",
        "pytz==2023.3",
        "python-dateutil==2.8.2",
    ],
    entry_points={
        "console_scripts": [
            "r2-sync=calendar_sync.__main__:main",
        ],
    },
) 