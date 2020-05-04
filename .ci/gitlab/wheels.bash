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

BUILDER_IMAGE=pymor/wheelbuilder_${MANYLINUX}_py${PYVER}:7868e7b59d6196dbcb5e1d2146723b15cb6745b8
docker pull ${BUILDER_IMAGE}
docker inspect  ${BUILDER_IMAGE}
docker run --rm --entrypoint=/bin/bash   \
     ${BUILDER_IMAGE} --version
