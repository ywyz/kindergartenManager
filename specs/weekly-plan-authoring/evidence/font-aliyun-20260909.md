# Aliyun font installation report

- Date: 2026-09-09 (Asia/Shanghai)
- SSH target alias: `aliyun`
- Remote OS: Ubuntu 24.04, Linux 6.8.0-106-generic, x86_64
- Remote account: `ecs-user` (UID 1000)
- Scope: host-level font installation only. No BWH/local font installation, repository edits, application deployment, container changes, database access, or secret-file access was performed.

## Source verification

The supplied files were verified locally before transfer:

| File | SHA-256 |
| --- | --- |
| `simsun.ttc` | `1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab` |
| `simsunb.ttf` | `2a476ca00b5fbbbc12a4c5335634722b11a495ed87429284325701f1e36b596a` |

The same hashes were verified in the remote transfer directory and after installation.

## Installation

- `sudo -n` was available for `ecs-user`.
- `fontconfig` was absent initially. The only package action was `apt-get install --no-install-recommends fontconfig`; the transaction reported `0 upgraded`, `1 newly installed`, and no service, container, or VM restart.
- Files were copied through a mode-0700 temporary directory and installed without overwriting an existing target.
- System-wide target: `/usr/local/share/fonts/km-simsun-20260909`
- Target directory: `root:root`, mode `0755`
- Font files: `root:root`, mode `0644`

Installed hashes:

```text
1526ac24375f51f6eb73bc2d3f8072dbe4a80a3a65217677c9d9a84f67dab2ab  /usr/local/share/fonts/km-simsun-20260909/simsun.ttc
2a476ca00b5fbbbc12a4c5335634722b11a495ed87429284325701f1e36b596a  /usr/local/share/fonts/km-simsun-20260909/simsunb.ttf
```

## Host-level acceptance

- Fontconfig: `2.15.0`
- `fc-match "SimSun"` resolved to:
  `/usr/local/share/fonts/km-simsun-20260909/simsun.ttc` with family `SimSun,宋体` and style `Regular,常规`.
- `fc-match "宋体"` resolved to the same file and family.
- `fc-scan` identified the TTC faces `SimSun,宋体` and `NSimSun,新宋体`; the TTF face was `SimSun-ExtB`.
- The font cache was rebuilt with `fc-cache -f` for the target directory.
- No `soffice` or `libreoffice` renderer is installed on this host; no renderer or business process was started.

This proves host-level fontconfig visibility on the Aliyun VM. It does not prove that a Docker/container renderer sees the host directory, nor does it provide Windows Word or a second-client result. A containerized renderer must have the font installed or mounted inside its own image/runtime before using this as layout evidence.

## Transfer-directory cleanup

- Before cleanup, `/tmp/km-wpa-fonts-20260909.Xjvw0f` was confirmed to be mode `0700`, owned by `ecs-user`, and to contain exactly the two transferred files with the hashes above.
- That exact temporary directory and its two transfer copies were removed with `rm` followed by `rmdir`.
- The directory now does not exist; the formal installation directory and both installed font hashes were rechecked and remain intact.
