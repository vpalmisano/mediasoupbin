import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mediasoupbin", # Replace with your own username
    version="0.1",
    author="Vittorio Palmisano",
    author_email="vpalmisano@gmail.com",
    description="Mediasoup plugin for GStreamer",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vpalmisano/mediasoupbin",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: AGPL-3.0",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    packages=setuptools.find_namespace_packages(include=['gst.*'])
)