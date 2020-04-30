#!/bin/sh

PYVER=$(python -c 'pyversions={"3.8":"cp38-cp38","3.7":"cp37-cp37m", "3.5":"cp35-cp35m", "3.6":"cp36-cp36m"}\
    ;import os;print(pyversions[os.environ["PYTHON_VERSION"]])')
export PYVER
PYBIN=/opt/python/${PYVER}/bin
export PYBIN
