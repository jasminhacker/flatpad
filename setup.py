import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="flatpad",
    version="1.0.0",
    author="Jonathan Hacker",
    author_email="github@jhacker.de",
    description="A simple webpage that provides a digital pad and indicates who is at home.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jonathanhacker/flatpad",
    classifiers=[
        "Framework :: Django",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    packages=["flatpad"],
    include_package_data=True,
    python_requires=">=3",
    install_requires=["bs4", "django", "fritzhome", "lxml", "netaddr", "netifaces",],
    scripts=["bin/flatpad"],
)
