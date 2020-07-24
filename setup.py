import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="nossinet",
    version="0.0.1",
    author="x4dr",
    author_email="x4dr@hotmail.com",
    description="pnp server, requirements are in requirements.txt",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/x4dr/NossiNet",
    packages=setuptools.find_packages(),
    install_requires=[
        "black",
        "pre-commit",
        "pydealer",
        "matplotlib",
        "pandas",
        "dateparser",
        "discord.py",
        "scipy",
        "bleach",
        "certifi",
        "chardet",
        "Click",
        "dnspython",
        "eventlet",
        "Flask",
        "Flask-SocketIO",
        "pyopenssl",
        "github-webhook",
        "greenlet",
        "idna",
        "itsdangerous",
        "Jinja2",
        "Markdown",
        "MarkupSafe",
        "monotonic",
        "numexpr",
        "python-socketio",
        "requests",
        "six",
        "urllib3",
        "webencodings",
        "Werkzeug",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPLv2",
        "Operating System :: Linux",
    ],
    python_requires=">=3.6",
)
