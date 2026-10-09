# Per-episode container image for the docker isolation tier (an episode's pi seats in one container) — built by
# docker_tier.py.
#
# The npm pin MUST stay in lockstep with pi_rpc.PI_PIN (the image tag carries it): the RPC event
# shapes, flags, and the labctl extension's registerTool surface were validated at exactly this
# version. On any bump, re-run the real-pi smoke before trusting new episodes.
#
# Never bake credentials into this image: the runner writes each seat's pi auth file into that
# seat's 0700 home at episode setup (see runner/docker_tier), so the key is neither in the image
# nor in any process environment a seat's shell inherits.
#
# procps: the per-turn watchdog kills a seat with `pkill -KILL -u <seat>` inside the container.
# python3/python-is-python3/git: the ordinary toolbox a shared research cluster login node carries
# (seats use python as a calculator and git/ls/find for exploration — all real in this tier).
FROM node:22-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 python-is-python3 git ca-certificates procps \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g @earendil-works/pi-coding-agent@0.77.0
