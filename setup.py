"""A setuptools based setup module.

See:
https://packaging.python.org/guides/distributing-packages-using-setuptools/
https://github.com/pypa/sampleproject
"""

import pathlib

# Always prefer setuptools over distutils
from setuptools import find_packages, setup

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")

setup(
    name="mindgard",  # Required
    version="0.21.0",
    # This is a one-line description or tagline of what your project does. This
    # corresponds to the "Summary" metadata field:
    # https://packaging.python.org/specifications/core-metadata/#summary
        description="Test your AI model's security without leaving your terminal.",  # Optional
    long_description=long_description,  # Optional
    long_description_content_type="text/markdown",  # Optional (see note above)
    # url="https://github.com/pypa/mindgard",  # TODO: when we get a pypi org add here
    author="Danny Hunt",  # Optional
    author_email="danny.hunt@mindgard.ai",  # Optional
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[  # Optional
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Security"
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
    ],
    keywords="ai, security, machine learning, llm, cybersecurity",  # Optional
    # package_dir={"": "src"},  # Optional
    # You can just specify package directories manually here if your project is
    # simple. Or you can use find_packages().
    #
    # Alternatively, if you just want to distribute a single Python file, use
    # the `py_modules` argument instead as follows, which will expect a file
    # called `my_module.py` to exist:
    #
    #   py_modules=["my_module"],
    #
    packages=find_packages(where="src"),  # Required
    python_requires=">=3.7, <4",
    # This field lists other packages that your project depends on to run.
    # Any package you put here will be installed by pip when your project is
    # installed, so they must be valid existing projects.
    #
    # For an analysis of "install_requires" vs pip's requirements files see:
    # https://packaging.python.org/discussions/install-requires-vs-requirements/
    install_requires=[],  # Optional
    extras_require={  # Optional
        "dev": ["mypy"],
    },
    # If there are data files included in your packages that need to be
    # installed, specify them here.
    package_data={  # Optional
        "sample": [],
    },
    # Entry points. The following would provide a command called `sample` which
    # executes the function `main` from this package when invoked:
    entry_points={  # Optional
        "console_scripts": [
            "mindgard=src.mindgard.__main__:main",
        ],
    },
    project_urls={  # Optional
        "Bug Reports": "https://github.com/Mindgard/cli/issues",
        "Find out more": "https://mindgard.ai/",
        "Source": "https://pypi.org/project/mindgard/",
    },
)