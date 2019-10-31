# build with something like this, where
#  -t is the name of the image
#  -f is this file
#  the . is a random directory
# docker build -t buildslave -f docker/Dockerfile .
#
# To create the buildslave configuration, call
# docker run --rm -v<build_dir>:/build_dir \
#    -eSLAVENAME=<name> -ePASSWORD=<password> buildslave
# Then you can examine the <build_dir>/buildbot.tac file.
#
# To run the buildslave (after the stage above succeeds) you no longer need the
# SLAVENAME and PASSWORD. The slave will run non-deamonized, which will appear
# to "hang" the console running the slave. To stop the slave, simply CTRL-C or
# kill the process.
#
# To enter the buildslave image
# docker run -it -v<abspath/to/builder/dir>:/build_dir> buildslave /bin/bash

FROM centos:centos6

RUN yum -y update
RUN yum install -y wget bzip2-devel zlib-devel glibc-devel libX11-devel \
   libXt-devel patch expat-devel libXft-devel openssl-devel tk-devel gdbm-devel \
   perl xz-devel libffi-devel ncurses-devel sqlite-devel
RUN yum install -y centos-release-scl

RUN wget https://github.com/squeaky-pl/centos-devtools/releases/download/8.2-s1/gcc-8.2.0-binutils-2.32-x86_64.tar.bz2 -O - | tar -C / -xj
RUN wget https://bitbucket.org/squeaky/portable-pypy/downloads/pypy-7.0.0-linux_x86_64-portable.tar.bz2 -O - | tar -C /opt -xj
RUN ln -s /opt/pypy-7.0.0-linux_x86_64-portable/bin/pypy /usr/local/bin/pypy

RUN yum install -y python27 python27-python-virtualenv

#yuck
ENV LD_LIBRARY_PATH=/opt/rh/python27/root/usr/lib64
RUN /opt/rh/python27/root/usr/bin/python -mvirtualenv /python27_virt
ENV PATH=/python27_virt/bin:$PATH
ENV PATH=/opt/devtools-8.2/bin:$PATH
RUN pip install --upgrade pip setuptools
RUN pip install buildbot-slave pytest hypothesis cffi vmprof mercurial

CMD if [ -e /build_dir/buildbot.tac ]; then \
    buildslave start --nodaemon /build_dir; \
  else \
    buildslave create-slave /build_dir buildbot.pypy.org:10407 $SLAVENAME $PASSWORD; \
  fi
