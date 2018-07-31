import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ndms2_client",
    version="0.0.3",
    author="Andrey F. Kupreychik",
    author_email="foxel@quickfox.ru",
    description="Keenetic NDMS2 client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/foxel/python_ndms2_client",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
