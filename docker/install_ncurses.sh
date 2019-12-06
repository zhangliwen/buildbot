#!/bin/bash
set -xe

mkdir ncurses
pushd ncurses
wget -q https://ftp.gnu.org/gnu/ncurses/ncurses-6.1.tar.gz
tar -xf ncurses-6.1.tar.gz --strip-components=1
./configure --prefix=/usr/local --enable-widec --without-tests --without-cxx --with-termlib --without-normal --with-shared --enable-database --with-terminfo-dirs=/lib/terminfo:/usr/share/terminfo
echo "#define NCURSES_USE_DATABASE 1" >> include/ncurses_cfg.h
make -j4
make install
popd
rm -rf  ncurses
