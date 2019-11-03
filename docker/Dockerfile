# build with something like this, where
#  -t is the name of the image
#  -f is this file
#  the . is a random directory
# docker build -t buildslave -f docker/Dockerfile docker 
#
# To create the buildslave configuration, call
# docker run --rm --user $UID -v<abspath/to/builder/dir>:/build_dir> \
#    -eSLAVENAME=<name> -ePASSWORD=<password> buildslave
# Then you can examine the <build_dir>/buildbot.tac file.
#
# To run the buildslave (after the stage above succeeds) you no longer need the
# SLAVENAME and PASSWORD. The slave will run non-deamonized, which will appear
# to "hang" the console running the slave. To stop the slave, simply CTRL-C or
# kill the process.
#
# You might want to keep the PYPY_USESSION_DIR where the testing/building
# artifacts are. Docker will not do this for you, so do something like this
# to save the files outside the docker
#
# mkdir -p build_dir/tmp
# docker run --rm --user $UID -v<abspath/to/builder/dir>:/build_dir> \
#     -ePYPY_USESSION_DIR=/build_dir/tmp buildslave
#
# To enter the buildslave image, add a shell command to the end
#
# docker run -it --user $UID -v<abspath/to/builder/dir>:/build_dir> \
#     -ePYPY_USESSION_DIR=/build_dir/tmp buildslave /bin/bash
#

FROM centos:centos6
WORKDIR /root

RUN yum -y update
RUN yum install -y wget bzip2-devel zlib-devel glibc-devel libX11-devel \
   libXt-devel patch expat-devel libXft-devel tk-devel gdbm-devel \
   perl xz-devel ncurses-devel sqlite-devel prelink

# get the gcc-8 devtools and pypy
RUN wget https://github.com/squeaky-pl/centos-devtools/releases/download/8.2-s1/gcc-8.2.0-binutils-2.32-x86_64.tar.bz2 -O - | tar -C / -xj
RUN wget https://bitbucket.org/squeaky/portable-pypy/downloads/pypy-7.0.0-linux_x86_64-portable.tar.bz2 -O - | tar -C /opt -xj
RUN ln -s /opt/pypy-7.0.0-linux_x86_64-portable/bin/pypy /usr/local/bin/pypy

ENV PATH=/opt/devtools-8.2/bin:$PATH

# Taken from pyca/infra/cryptography-manylinux
# centos6 libffi is buggy, download and use a newer one
# also use the version of openssl that latests pyca/cryptography uses
ADD install_libffi.sh /root/install_libffi.sh
ADD install_openssl.sh /root/install_openssl.sh
RUN sh install_libffi.sh manylinux2010 2>&1 | tee /root/install_libffi.log
RUN sh install_openssl.sh manylinux2010 2>&1 | tee /root/install_openssl.log

RUN yum install -y centos-release-scl
RUN yum install -y python27 python27-python-virtualenv

# build a python 2.7 virtualenv, use the scl-installed version of python2.7
# since centos6 itself has python2.6
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64
RUN /opt/rh/python27/root/usr/bin/python -mvirtualenv /python27_virt
ENV PATH=/python27_virt/bin:$PATH
RUN pip install --upgrade pip setuptools
RUN pip install buildbot-slave pytest hypothesis cffi vmprof mercurial
ENV PKG_CONFIG_PATH=/usr/local/lib64/pkgconfig

CMD if [ -e /build_dir/buildbot.tac ]; then \
    buildslave start --nodaemon /build_dir; \
  else \
    buildslave create-slave /build_dir buildbot.pypy.org:10407 $SLAVENAME $PASSWORD; \
  fi
