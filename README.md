# Python CM4 Fan Controller

![GitHub release (latest by date)](https://img.shields.io/github/v/release/alanbchristie/python-cm4-fan-controller)

[![build](https://github.com/alanbchristie/python-cm4-fan-controller/actions/workflows/build.yaml/badge.svg)](https://github.com/alanbchristie/python-cm4-fan-controller/actions/workflows/build.yaml)

[![License](http://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat)](https://github.com/alanbchristie/python-cm4-fan-controller/blob/master/LICENSE.txt)

[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Packaged with Poetry](https://img.shields.io/badge/packaging-poetry-cyan.svg)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A temperature-based fan controller for the Compute Module 4 IO board.

## Contributing
The project uses: -

- [pre-commit] to enforce linting of files prior to committing them to the upstream repository
- [Commitizen] to enforce a [Conventional Commit] commit message format
- [Black] and [isort] as a code formatter

You MUST comply with these choices in order to contribute to the project.

To get started review the pre-commit utility and the conventional commit style
and then set-up your local clone by following the Installation and Quick Start sections: -

    poetry shell
    poetry install
    pre-commit install -t commit-msg -t pre-commit

Now the project's rules will run on every commit, and you can check the current health
of your clone with: -

    pre-commit run --all-files

---

[black]: https://black.readthedocs.io/en/stable/
[commitizen]: https://commitizen-tools.github.io/commitizen/
[conventional commit]: https://www.conventionalcommits.org/en/v1.0.0/
[isort]: https://pycqa.github.io/isort/
[pre-commit]: https://pre-commit.com
