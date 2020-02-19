import setuptools

setuptools.setup(
    name="sapi",
    version="1.0",
    author="William Howell",
    author_email="whowell@rc.ufl.edu",
    description="A REST API for Slurm",
    url="https://github.com/UFResearchComputing/slurm-api",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
