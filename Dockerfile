FROM themattrix/tox

RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt-get install -y nodejs bzip2
