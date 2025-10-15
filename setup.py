from pathlib import Path
from setuptools import setup, find_packages
from magic_pdf.libs.version import __version__


def parse_requirements(filename):
    with open(filename) as f:
        lines = f.read().splitlines()

    requires = []

    for line in lines:
        if "http" in line:
            pkg_name_without_url = line.split('@')[0].strip()
            requires.append(pkg_name_without_url)
        else:
            requires.append(line)

    return requires


if __name__ == '__main__':
    with Path(Path(__file__).parent,
              'README.md').open(encoding='utf-8') as file:
        long_description = file.read()
    setup(
        name="magic_pdf",
        version=__version__,
        packages=find_packages() + ["magic_pdf.resources"],
        package_data={
            "magic_pdf.resources": ["**"],
        },
        install_requires=parse_requirements('requirements.txt'),
        description="MonkeyOCR: Document Parsing with a Structure-Recognition-Relation Triplet Paradigm",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/Yuliang-Liu/MonkeyOCR",
        python_requires=">=3.9",
        include_package_data=True,
        zip_safe=False,
    )
