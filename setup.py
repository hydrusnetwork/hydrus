'''
:author: Leandro (Cerberus1746) Benedet Garcia
'''
try:
    from sphinx.setup_command import BuildDoc
    SPHINX_LOADED = True
except(ModuleNotFoundError, ImportError):
    SPHINX_LOADED = False

import setuptools
from hydrus.include.HydrusConstants import SOFTWARE_VERSION

if SPHINX_LOADED:
    CMDCLASS = {'build_sphinx': BuildDoc}

NAME = 'hydrus'
AUTHOR = ""
AUTHOR_EMAIL = ""

__version__ = SOFTWARE_VERSION
with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

with open("COPYING", "r") as fh:
    LICENSE = fh.read()

with open("requirements.txt", "r") as fh:
    REQUIREMENTS = fh.read().strip().split("\n")

with open("requirements-tests.txt", "r") as fh:
    TEST_PACKAGES = fh.read().strip().split("\n")

with open("requirements-docs.txt", "r") as fh:
    REQUIREMENTS_DOCS = fh.read().strip().split("\n")

setuptools.setup(
    name=NAME,
    version=__version__,
    cmdclass=CMDCLASS if SPHINX_LOADED else {},
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    description="Data management system with modding and Panda3D engine in mind.",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    license="MIT License",
    python_requires=">=3.7",
    url="https://github.com/Cerberus1746/PandaCoreData",
    tests_require=TEST_PACKAGES,
    packages=setuptools.find_packages(),
    scripts=['scripts/hydrus_client.py', 'scripts/hydrus_client.py'],
    include_package_data=True,
    zip_safe=False,
    extras_require={
        'tests': TEST_PACKAGES,
        'docs': REQUIREMENTS_DOCS
    },
    install_requires=REQUIREMENTS,
    classifiers=[],
    command_options={
        'build_sphinx': {
            'project': ('setup.py', NAME),
            'version': ('setup.py', __version__),
            'source_dir': ('setup.py', 'docs/source'),
            'build_dir': ('setup.py', 'docs/build'),
        }
    } if SPHINX_LOADED else {},
)
