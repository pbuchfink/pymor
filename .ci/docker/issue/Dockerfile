
FROM pymor/pypi-mirror_oldest_py3.6:8c5aa9f7b5215a8849378bf0b2a261bee1752319 as dependencies

FROM quay.io/pypa/manylinux2010_x86_64:2020-04-06-694ff3c

MAINTAINER René Fritze <rene.fritze@wwu.de>


ENV MPICC=/usr/lib64/openmpi/bin/mpicc \
    PYTHON_VERSION=3.6 \
    WHEEL_DIR=/io/wheelhouse

COPY gosu.gpg /tmp/
RUN yum install -y atlas-devel openmpi-devel sudo \
        fltk freeglut libpng libjpeg \
        tk tcl xorg-x11-server-Xvfb xauth && \
    yum install -y gpg && gpg --import /tmp/gosu.gpg \
    && curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.11/gosu-amd64" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.11/gosu-amd64.asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && rm -r /root/.gnupg/ \
    && chmod +x /usr/local/bin/gosu

COPY --from=dependencies /pymor/downloads/* ${WHEEL_DIR}/
COPY pybin.sh /etc/profile.d/
# some packages get installed manually because others haev broken dependency settings
RUN source /etc/profile.d/pybin.sh && \
  rm ${WHEEL_DIR}/slycot* && \
  ${PYBIN}/pip install --no-cache ${WHEEL_DIR}/numpy* ${WHEEL_DIR}/scipy* && \
  ${PYBIN}/pip install --no-cache ${WHEEL_DIR}/*

COPY entrypoint.sh /usr/local/bin/
COPY build-wheels.sh /usr/local/bin/

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/usr/local/bin/build-wheels.sh"]
