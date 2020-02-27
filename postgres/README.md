# Docker image for testing orange database connectors

It is based on [`official postgres docker`](https://hub.docker.com/_/postgres) extended with quantile and tsm_system_time plugins. Image is hosted [`here.`](https://hub.docker.com/r/orangedm/)

This is mainly used by our [`CI`](https://github.com/biolab/orange3/blob/master/.github/workflows/linux_workflow.yml#L23) but can be used elsewhere.
