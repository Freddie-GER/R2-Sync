from setuptools import setup, find_packages

setup(
    name="calendar_sync",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "caldav==1.3.6",
        "python-dotenv==1.0.0",
        "requests==2.31.0",
        "icalendar==5.0.11",
        "pytz==2023.3",
        "python-dateutil==2.8.2"
    ],
    entry_points={
        'console_scripts': [
            'calendar-sync=calendar_sync.__main__:main',
        ],
    },
) 