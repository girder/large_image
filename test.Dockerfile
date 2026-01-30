FROM ubuntu:24.04

# This is mostly based on the Dockerfiles from themattrix/pyenv and
# themattrix/tox-base.  It has some added packages, most notably liblzma-dev,
# to work for more of our conditions, plus some convenience libraries like
# libldap2-dev, libsasl2-dev, fuse to facilitate girder-based testing.  Also,
# gosu was removed.

LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

ARG NODE_VERSION=14
ARG PYTHON_VERSIONS="3.11 3.9 3.10 3.12 3.13 3.14"

# The default python version will be the first of all the versions listed
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    PYENV_ROOT="/.pyenv" \
    PATH="/.pyenv/bin:/.pyenv/shims:$PATH"

# Consumers of this package aren't expecting an existing ubuntu user (there
# wasn't one in the ubuntu:22.04 base)
RUN userdel -r ubuntu 2>/dev/null

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      # general utilities \
      #  We had been installing \
      # software-properties-common \
      #  but this includes a copy of python which we will install later, so \
      #  install some of its component parts without python (see \
      #  https://packages.debian.org/stable/software-properties-common) \
      gir1.2-glib-2.0 \
      gpg \
      iso-codes \
      lsb-release \
      # as specified by \
      # https://github.com/pyenv/pyenv/wiki#suggested-build-environment \
      build-essential \
      curl \
      libffi-dev \
      liblzma-dev \
      libreadline-dev \
      libsqlite3-dev \
      tk-dev \
      wget \
      xz-utils \
      zlib1g-dev \
      # for curl \
      ca-certificates \
      # girder convenience \
      fuse \
      libldap2-dev \
      libsasl2-dev \
      # developer convenience \
      bzip2 \
      dirmngr \
      git \
      less \
      locales \
      vim \
      # testing convenience \
      fonts-dejavu \
      libmagic-dev \
      # shrink docker image \
      rdfind \
      # core girder \
      iptables \
      dnsutils \
      universal-ctags \
      && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    find /usr/share/locale -mindepth 1 -maxdepth 1 ! -name 'en_US*' ! -name 'C' ! -name 'en' -type d -exec rm -rf {} + && \
    find /usr/share/i18n -mindepth 1 ! -name 'en_US*' ! -name 'C' -type f -exec rm -f {} + && \
    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash && \
    find / -xdev -name __pycache__ -type d -exec rm -r {} \+ && \
    rm -rf /etc/ssh/ssh_host* && \
    rm -rf /usr/share/vim/vim91/doc/* /usr/share/vim/vim91/tutor/* /usr/share/doc && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /var/cache/* && \
    rdfind -minsize 8192 -makehardlinks true -makeresultsfile false /usr && \
    rdfind -minsize 8192 -makehardlinks true -makeresultsfile false /var

RUN pyenv update && \
    pyenv install --list && \
    echo $PYTHON_VERSIONS | xargs -P `nproc` -n 1 pyenv install && \
    # ensure newest pip and setuptools for all python versions \
    echo $PYTHON_VERSIONS | xargs -n 1 bash -c 'pyenv global "${0}" && pip install -U setuptools pip' && \
    pyenv global $(pyenv versions --bare) && \
    find $PYENV_ROOT/versions -type d '(' -name '__pycache__' -o -name 'test' -o -name 'tests' ')' -exec rm -rfv '{}' + >/dev/null && \
    find $PYENV_ROOT/versions -type f '(' -name '*.py[co]' -o -name '*.exe' ')' -exec rm -fv '{}' + >/dev/null && \
    echo $PYTHON_VERSIONS | tr " " "\n" > $PYENV_ROOT/version && \
    find / -xdev -name __pycache__ -type d -exec rm -r {} \+ && \
    rm -rf /tmp/* /var/tmp/* /root/.cache/* && \
    find /.pyenv '(' -name '*.so' -o -name '*.a' -o -name '*.so.*' ')' -exec strip --strip-unneeded -p -D {} \; && \
    find /.pyenv -name 'libpython*.a' -delete && \
    # This makes duplicate python library files hardlinks of each other \
    rdfind -minsize 8192 -makehardlinks true -makeresultsfile false /.pyenv

RUN for ver in $PYTHON_VERSIONS; do \
    pyenv local $ver && \
    python -m pip install --no-cache-dir -U pip && \
    python -m pip install --no-cache-dir tox wheel && \
    pyenv local --unset; \
    done && \
    pyenv rehash && \
    find / -xdev -name __pycache__ -type d -exec rm -r {} \+ && \
    rm -rf /tmp/* /var/tmp/* && \
    rdfind -minsize 8192 -makehardlinks true -makeresultsfile false /.pyenv

# Use nvm to install node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash && \
    . ~/.bashrc && \
    if [ "$NODE_VERSION" = "14" ]; then \
    cd /root/.nvm/versions/node/v14.21.3/lib && \
    # upgrade packages to avoid security issues \
    npm install 'form-data@^2.5.5' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm && \
    npm install 'brace-expansion@^1.1.12' && \
    npm install 'cross-spawn@^6.0.6' && \
    npm install 'form-data@^2.5.5' && \
    npm install 'http-cache-semantics@^4.1.1' && \
    npm install 'qs@^6.14.1' && \
    npm install 'semver@^5.7.2' && \
    # ip package has an unaddressed HIGH CVE, ip-address is a direct substitute \
    npm install --no-save ip-address && \
    rm -rf node_modules/ip && \
    mv node_modules/ip-address node_modules/ip && \
    # update subpackages that need it \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/term-size && \
    npm install 'cross-spawn@^6.0.6' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/execa && \
    npm install 'cross-spawn@^6.0.6' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/request && \
    npm install 'form-data@^2.5.5' && \
    npm install 'qs@^6.14.1' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/string-width && \
    npm install 'ansi-regex@^3.0.1' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/yargs && \
    npm install 'ansi-regex@^4.1.1' && \
    cd /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/make-fetch-happen && \
    npm install 'http-cache-semantics@^4.1.1' && \
    # We can't actually upgrade tar past 6.x \
    sed -i 's/4\.4\.19/*/g' /root/.nvm/versions/node/v14.21.3/lib/node_modules/npm/node_modules/tar/package.json && \
    true; else \
    npm install -g npm@latest && \
    true; fi && \
    rm -rf /root/.nvm/.cache && \
    npm config set fetch-timeout 600000 && \
    npm cache clean --force && \
    ln -s $(dirname `which npm`) /usr/local/node && \
    rdfind -minsize 1024 -makehardlinks true -makeresultsfile false /root/.nvm

ENV PATH="/usr/local/node:$PATH"

WORKDIR /app
