import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as req:
    dependencies = [line.strip('\n') for line in req.readlines()]

setuptools.setup(
    name="ftx",
    version="0.0.1",
    author="",
    author_email="",
    description="FTX exchange trade statistics tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=dependencies,
)
