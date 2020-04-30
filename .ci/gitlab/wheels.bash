#!/bin/bash

set -e

if [[ "x${CI_COMMIT_TAG}" == "x" ]] ; then
    sed -i -e 's;style\ \=\ pep440;style\ \=\ ci_wheel_builder;g' setup.cfg
fi

set -u
MANYLINUX=manylinux${1}
shift

# since we're in a d-in-d setup this needs to a be a path shared from the real host
BUILDER_WHEELHOUSE=${SHARED_PATH}
PYMOR_ROOT="$(cd "$(dirname ${BASH_SOURCE[0]})" ; cd ../../ ; pwd -P )"
cd "${PYMOR_ROOT}"

set -x
mkdir -p ${BUILDER_WHEELHOUSE}

BUILDER_IMAGE=pymor/wheelbuilder_${MANYLINUX}_py${PYVER}:${PYPI_MIRROR_TAG}
docker pull ${BUILDER_IMAGE}
docker run --rm -e LOCAL_USER_ID=$(id -u)  \
     ${BUILDER_IMAGE} ls
