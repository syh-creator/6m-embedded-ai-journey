from setuptools import setup,find_packages
setup(
    name="sensim",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0",
        "matplotlib>=3.5",
        "numpy>=1.21",
        "scipy>=1.7",
        "pytest>=6.2"
    ],
    entry_points={
        "console_scripts": [
            "sensim = sensim.cli:cli",
        ],
    },
)
    

 