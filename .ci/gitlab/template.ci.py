#!/usr/bin/env python3

tpl = '''# THIS FILE IS AUTOGENERATED -- DO NOT EDIT #
#   Edit and Re-run .ci/gitlab/template.ci.py instead       #

stages:
  - sanity
  - test
  - build
  - install_checks
  - deploy

.test_base:
    retry:
        max: 2
        when:
            - runner_system_failure
            - stuck_or_timeout_failure
            - api_failure
    only: ['branches', 'tags', 'triggers', 'merge-requests']
    except:
        - /^staging/.*$/i

.pytest:
    extends: .test_base
    script: .ci/gitlab/script.bash
    tags:
      - long execution time
    environment:
        name: unsafe
    stage: test
    before_script:
    # switches default index to pypi-mirror service
      - mkdir ~/.config/pip/ && cp /usr/local/share/ci.pip.conf ~/.config/pip/pip.conf
    after_script:
      - .ci/gitlab/after_script.bash
    artifacts:
        name: "$CI_JOB_STAGE-$CI_COMMIT_REF_SLUG"
        expire_in: 3 months
        paths:
            - src/pymortests/testdata/check_results/*/*_changed
            - coverage.xml
            - memory_usage.txt
        reports:
            junit: test_results.xml

.docker-in-docker:
    tags:
      - docker-in-docker
    extends: .test_base
    retry:
        max: 2
        when:
            - always
    image: docker:stable
    variables:
        DOCKER_HOST: tcp://docker:2375/
        DOCKER_DRIVER: overlay2
    before_script:
        - apk --update add openssh-client rsync git file bash python3 curl make
        # hotfix for https://github.com/jupyter/repo2docker/issues/755
        - pip3 install ruamel.yaml==0.15.100
        - pip3 install jinja2 jupyter-repo2docker docker-compose
        - 'export SHARED_PATH="${CI_PROJECT_DIR}/shared"'
        - mkdir -p ${SHARED_PATH}
    services:
        - docker:dind
    environment:
        name: unsafe

# this should ensure binderhubs can still build a runnable image from our repo
.binder:
    extends: .docker-in-docker
    stage: install_checks
    variables:
        IMAGE: ${CI_REGISTRY_IMAGE}/binder:${CI_COMMIT_REF_SLUG}
        CMD: "jupyter nbconvert --to notebook --execute /pymor/.ci/ci_dummy.ipynb"
        USER: juno

repo2docker:
    extends: .binder
    script:
        - repo2docker --user-id 2000 --user-name ${USER} --no-run --debug --image-name ${IMAGE} .
        - docker login -u $CI_REGISTRY_USER -p $CI_REGISTRY_PASSWORD $CI_REGISTRY
        - docker run ${IMAGE} ${CMD}
        - docker push ${IMAGE}

local_jupyter:
    extends: .binder
    script:
        - make docker_image
        - cd .binder
        - docker-compose run jupyter ${CMD}

.wheel:
    extends: .docker-in-docker
    stage: build
    only: ['branches', 'tags', 'triggers']
    variables:
        TEST_OS: "{{ ' '.join(testos) }}"
    artifacts:
        paths:
        # cannot use exported var from env here
        - ${CI_PROJECT_DIR}/shared/pymor*manylinux*whl
        expire_in: 1 week

sanity:
    extends: .docker-in-docker
    stage: sanity
    script: ./.ci/gitlab/ci_sanity_check.bash

# THIS FILE IS AUTOGENERATED -- DO NOT EDIT #
#   Edit and Re-run .ci/gitlab/template.ci.py instead       #

'''


import os
import jinja2
import sys
from itertools import product
tpl = jinja2.Template(tpl)
pythons = ['3.6', '3.7']
# these should be all instances in the federation
marker = ["Vanilla", "PIP_ONLY", "NOTEBOOKS", "MPI"]
binder_urls = ['https://gke.mybinder.org/build/gh/pymor/pymor',
               'https://ovh.mybinder.org/build/gh/pymor/pymor']
testos = ['centos_8', 'debian_buster', 'debian_testing']
ci_image_tag = open(os.path.join(os.path.dirname(__file__), '..', 'CI_IMAGE_TAG'), 'rt').read()
pypi_mirror_tag = open(os.path.join(os.path.dirname(__file__), '..', 'PYPI_MIRROR_TAG'), 'rt').read()
with open(os.path.join(os.path.dirname(__file__), 'ci.yml'), 'wt') as yml:
    matrix = list(product(pythons, marker))
    yml.write(tpl.render(**locals()))
