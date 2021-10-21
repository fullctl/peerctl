FROM python:3.9-alpine as base

ARG virtual_env=/venv
ARG install_to=/srv/service
ARG build_deps=""
ARG run_deps=" \
    libgcc \
    postgresql-libs \
    "



# env to pass to sub images
ENV BUILD_DEPS=$build_deps
ENV RUN_DEPS=$run_deps
ENV SERVICE_HOME=$install_to
ENV VIRTUAL_ENV=$virtual_env
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV POETRY_VERSION=1.1.11


# build container
FROM ghcr.io/fullctl/fullctl-builder-alpine:prep-release as builder

WORKDIR /build

# individual files here instead of COPY . . for caching
COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root

COPY Ctl/VERSION Ctl/


#### final image

FROM base as final

ARG uid=5002
ARG USER=acctsvc

# extra settings file if needed
# TODO keep in until final production deploy
ARG COPY_SETTINGS_FILE=mainsite/settings/dev.py

# add dependencies
RUN apk add $RUN_DEPS

RUN adduser -Du $uid $USER

WORKDIR $SERVICE_HOME
COPY --from=builder "$VIRTUAL_ENV" "$VIRTUAL_ENV"

RUN mkdir -p etc locale media static
COPY Ctl/VERSION etc/
COPY docs/ docs

RUN chown -R $USER:$USER locale media

#### entry point from final image, not tester
FROM final

COPY src/ main/
COPY Ctl/docker/entrypoint.sh .
RUN ln -s $SERVICE_HOME/entrypoint.sh /entrypoint
RUN ln -s /venv $SERVICE_HOME/venv

COPY Ctl/docker/django-uwsgi.ini etc/
COPY Ctl/docker/manage.sh /usr/bin/manage


ENV UWSGI_SOCKET=127.0.0.1:6002

USER $USER

ENTRYPOINT ["/entrypoint"]
CMD ["runserver"]
