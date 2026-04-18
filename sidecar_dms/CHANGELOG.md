# Changelog

## 0.1.1

- Fix `/data` permission denied: entrypoint chowns the volume and drops to
  the unprivileged user via gosu when started as root (HA case).

## 0.1.0

- Initial Home Assistant add-on packaging.
