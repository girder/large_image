FROM ubuntu:20.04

# This is mostly based on the Dockerfiles from themattrix/pyenv and
# themattrix/tox-base.  It has some added packages, most notably liblzma-dev,
# to work for more of our conditions, plus some convenience libraries like
# libldap2-dev, libsasl2-dev, fuse to facilitate girder-based testing.

LABEL maintainer="Kitware, Inc. <kitware@kitware.com>"

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=en_US.UTF-8 \
    PYENV_ROOT="/.pyenv" \
    PATH="/.pyenv/bin:/.pyenv/shims:$PATH" \
    PYTHON_VERSIONS="3.9.5 3.8.10 3.7.10 3.6.13"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      build-essential \
      bzip2 \
      ca-certificates \
      curl \
      dirmngr \
      fonts-dejavu \
      fuse \
      git \
      gosu \
      gpg-agent \
      less \
      libbz2-dev \
      libffi-dev \
      libldap2-dev \
      liblzma-dev \
      libmagic-dev \
      libncurses5-dev \
      libncursesw5-dev \
      libreadline-dev \
      libsasl2-dev \
      libsqlite3-dev \
      libssl-dev \
      libxml2-dev \
      libxmlsec1-dev \
      llvm \
      locales \
      make \
      software-properties-common \
      ssh \
      tk-dev \
      vim \
      wget \
      xz-utils \
      zlib1g-dev \
      && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    curl -L https://github.com/pyenv/pyenv-installer/raw/master/bin/pyenv-installer | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN pyenv update && \
    pyenv install --list && \
    echo $PYTHON_VERSIONS | xargs -P `nproc` -n 1 pyenv install && \
    pyenv global $(pyenv versions --bare) && \
    find $PYENV_ROOT/versions -type d '(' -name '__pycache__' -o -name 'test' -o -name 'tests' ')' -exec rm -rfv '{}' + >/dev/null && \
    find $PYENV_ROOT/versions -type f '(' -name '*.py[co]' -o -name '*.exe' ')' -exec rm -fv '{}' + >/dev/null && \
    echo $PYTHON_VERSIONS | tr " " "\n" > $PYENV_ROOT/version && \
    rm -rf /tmp/* /var/tmp/*

RUN for ver in $PYTHON_VERSIONS; do \
    pyenv local $ver && \
    python -m pip install --no-cache-dir -U pip && \
    python -m pip install --no-cache-dir tox wheel && \
    pyenv local --unset; \
    done && \
    pyenv rehash && \
    rm -rf /tmp/* /var/tmp/*

# Create a user that can be used with gosu or chroot when running tox
RUN groupadd -r tox --gid=999 && \
    useradd -m -r -g tox --uid=999 tox

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /app
