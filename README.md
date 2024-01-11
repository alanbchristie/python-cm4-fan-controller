# Python CM4 Fan Controller

![GitHub release (latest by date)](https://img.shields.io/github/v/release/alanbchristie/python-cm4-fan-controller)

[![build](https://github.com/alanbchristie/python-cm4-fan-controller/actions/workflows/build.yaml/badge.svg)](https://github.com/alanbchristie/python-cm4-fan-controller/actions/workflows/build.yaml)

[![License](http://img.shields.io/badge/license-Apache%202.0-blue.svg?style=flat)](https://github.com/alanbchristie/python-cm4-fan-controller/blob/master/LICENSE.txt)

[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-yellow.svg)](https://conventionalcommits.org)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Packaged with Poetry](https://img.shields.io/badge/packaging-poetry-cyan.svg)](https://python-poetry.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A temperature-based fan controller for the Compute Module 4 (CM4) IO board.

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

## Hardware
This code is designed to tun on the CM4 IO board where, according to the
[CM4 datasheet], to enable the I2C bus to the fan controller,
you will need `dtparam=i2c_vc=on` set in your `/boot/config.txt`.
The fan controller will then be on i2c-10 at the 7-bit address 0x2f.

The fan I'm using is a Waveshare, part number [CM4-FAN-3007-12V].

The practical fan speed range (found empirically) is between between 45 (18%)
and 255 (100%). The fastest speed while still remaining quiet is about 70 (27%).

## Installation
You typically run the controller as a systemd service on the CM IO board.
The repository contains an example service file that you can use as a template.

Clone the repository to your CM4 IO board and install the service file: -

    git clone https://github.com/alanbchristie/python-cm4-fan-controller
    cd python-cm4-fan-controller

Edit the `cm4-fan-controller.service` file to suite your needs and then install it: -

    sudo cp cm4-fan-controller.service /lib/systemd/system
    sudo chmod 644 /lib/systemd/system/cm4-fan-controller.service
    sudo systemctl daemon-reload
    sudo systemctl enable cm4-fan-controller.service

And then reboot the CM4 to make suer the service starts automatically on boot.

    sudo reboot

---

[black]: https://black.readthedocs.io/en/stable/
[commitizen]: https://commitizen-tools.github.io/commitizen/
[conventional commit]: https://www.conventionalcommits.org/en/v1.0.0/
[cm4 datasheet]: https://datasheets.raspberrypi.com/cm4io/cm4io-datasheet.pdf
[CM4-FAN-3007-12V]: https://www.waveshare.com/cm4-fan-3007.htm
[isort]: https://pycqa.github.io/isort/
[pre-commit]: https://pre-commit.com
