<div align="center">

<img src="https://avatars.githubusercontent.com/u/34251619?v=4" align="center" width="144px" height="144px"/>

### NAS-as-Code

_... managed with Ansible and GitHub Actions_ 🤖

[![Validation](https://github.com/osotechie/nas-as-code/actions/workflows/validation.yml/badge.svg)](https://github.com/osotechie/nas-as-code/actions/workflows/validation.yml) [![Provision](https://github.com/osotechie/nas-as-code/actions/workflows/provision.yml/badge.svg)](https://github.com/osotechie/nas-as-code/actions/workflows/provision.yml) [![Updates](https://github.com/osotechie/nas-as-code/actions/workflows/updates.yml/badge.svg)](https://github.com/osotechie/nas-as-code/actions/workflows/updates.yml)

</div>

---

## 📖 Overview

This repo codifies the build, configuration, and ongoing management of my home NAS using [Ansible](https://www.ansible.com/) and [GitHub Actions](https://github.com/features/actions). The goal is full Infrastructure as Code (IaC) — the NAS can be provisioned from scratch, updated, and restored entirely from this repository.

### 🏁 Project Objectives

The main objectives of the project are:

1. ✅ Codify the build and configuration of the base NAS
   - ✅ Install the latest packages and updates
   - ✅ Ensure required user accounts are present
   - ✅ Ensure required folder structure is present
   - ✅ Configure roles
     - ✅ Docker - to allow deployment of docker containers on the NAS
     - ✅ Storage - to configure / mount storage correctly for the NAS
     - ✅ Samba - to allow network based access to NAS storage
     - ✅ Backup - to ensure backup jobs are configured to protect data
     - ✅ UPS Monitoring - to ensure NAS shuts down when UPS is running low
     - ✅ Coral TPU - ensure Coral TPU is driver is installed
2. [ ] Restore NAS state from latest backup (if required)
   - [ ] Restore persistent docker data from network backup
   - [ ] Initiate re-deployment of Docker Stacks from [NAS-Docker](https://github.com/osotechie/nas-docker)
3. ✅ Codify on-going management tasks for the NAS
   - ✅ Automatic updates and reboots (if required)

<br>

---

<br>

## 🏗️ Repository Structure
<br>
I have created the following structure to manage this project. I have developed the structure to make to solution as modular as possible.

```
nas-as-code/
├── .github/
│   ├── dependabot.yml                  # Automated dependency updates for pinned Actions
│   └── workflows/
│       ├── validation.yml              # CI — lint & syntax checks on push (non-main)
│       ├── deploy.yml                  # CD — provision via Ansible on PR merge to main
│       └── updates.yml                 # Scheduled — weekly OS updates (Tue 2AM UTC)
├── ansible/
│   ├── ansible.cfg                     # Ansible configuration (inventory path, roles path)
│   ├── inventory/
│   │   ├── environments.yml            # Host definitions for test & production
│   │   └── group_vars/
│   │       ├── test.yml                # Variables for the test environment
│   │       └── production.yml          # Variables for the production environment
│   └── playbooks/
│       ├── provision.yml               # Full NAS provisioning playbook
│       ├── updates.yml                 # OS package updates & reboot if required
│       └── roles/
│           ├── owendemooy.docker/      # Installs Docker CE & Compose
│           ├── owendemooy.storage/     # Configures MergerFS storage pool
│           ├── owendemooy.samba/       # Sets up Samba file shares
│           ├── owendemooy.nut-client/  # NUT UPS monitoring client
│           ├── owendemooy.nas-backup/  # Nightly rsync backup with WOL
│           └── owendemooy.coraltpu/    # Google Coral TPU driver & runtime
└── .gitignore
```
<br>
<br>

## 🌍 Environments
<br>
The inventory files are used to define two environments, each with their own matching GitHub Environment for secrets / variables:
<br>

| Environment | Host | Purpose |
|-------------|------|---------|
| `test` | `nas-build-test` | Test VM to validate all changes |
| `production` | `nas` | The production NAS |

Environment-specific configuration lives in `inventory/group_vars/{environment}.yml` and includes:
- `functions` — which roles to apply
- `apt_packages` — additional packages to install
- `users` — user accounts and SSH keys
- `host_directories` — required directories with ACLs
- `samba_users` / `samba_shares` — Samba configuration

<br>
<br>

## 🔧 Playbooks
<br>
The heavy lifting for the actual provisioning and updating is done using Ansible Playbooks. I have create two main Playbooks for this project to handle the provison and updates of the NAS.


### 🏗️ Provision

The `provision.yml` playbook performs a full host setup:

1. **Packages** — Upgrades all packages and installs additional required packages
2. **Host entries** — Ensures `/etc/hosts` contains all managed hosts
3. **Users** — Creates required user accounts and configures SSH authorized keys
4. **Directories** — Creates required directory structure with correct ACLs
5. **Roles** — Conditionally applies roles based on the `functions` variable:

   | Role | Function | Purpose |
   |------|----------|---------|
   | `owendemooy.docker` | `docker` | Docker CE & Compose installation |
   | `owendemooy.storage` | `storage` | MergerFS disk pool configuration |
   | `owendemooy.samba` | `samba` | SMB file sharing |
   | `owendemooy.nut-client` | `nut-client` | UPS monitoring via NUT |
   | `owendemooy.nas-backup` | `nas-backup` | Nightly rsync backup with wake-on-LAN |
   | `owendemooy.coraltpu` | `coraltpu` | Google Coral Edge TPU drivers |

<br>

### ♻️ Updates

The `updates.yml` playbook handles routine OS maintenance:

1. **Package upgrade** — Installs the latest available versions of all installed packages via `apt upgrade`
2. **Reboot check** — Inspects `/var/run/reboot-required` to determine if a restart is needed (e.g. kernel update)
3. **Safe reboot** — If required, reboots the host and waits for it to come back online (up to 5 minutes)

<br>
<br>

## 🚀 GitHub Actions
<br>
I am using GitHub Actions to control the validation, provisioning and updates to my NAS. The GitHub actions have been designed to validate and test all changes again the test environment, before applying any changes to Production.
<br>

### Validation (CI)

**File:** `.github/workflows/validation.yml`
**Trigger:** Any push to a non-main branch, or manual dispatch.

| Step | Description |
|------|-------------|
| Install dependencies | Installs `ansible-dev-tools` and the `ansible.posix` collection |
| Syntax check | Runs `ansible-playbook --syntax-check` on all playbooks |
| Ansible Lint | Lints playbooks and roles using Code Climate format for reporting |
| Test Report | Generates a markdown summary with findings table viewable on the Actions run page |
| SARIF Upload | Publishes lint findings to GitHub Code Scanning (inline PR annotations) |
| Fail gate | Fails the workflow if any lint violations are found |
| Microsoft Security DevOps | Scans with Checkov and Trivy for security misconfigurations and vulnerabilities |
| Upload Security SARIF | Publishes security findings to GitHub Code Scanning |

<br>

### Provision (CD)

**File:** `.github/workflows/provision.yml`
**Trigger:** Pull request merged to `main` (ignoring markdown-only changes).

Deploys sequentially to **test** then **production** using a matrix strategy (`fail-fast: true`, `max-parallel: 1`). If test fails, production is skipped.

| Step | Description |
|------|-------------|
| Azure Login | Authenticates to Azure for KeyVault access |
| Get Secrets | Pulls secrets from Azure KeyVault into the runner environment |
| Replace Tokens | Substitutes `#{TOKEN}#` placeholders in config files with real values |
| WireGuard VPN | Connects to home network via WireGuard tunnel |
| Add Routes | Adds a route to the target host over WireGuard |
| SSH Setup | Configures SSH keys, pinned host fingerprints, and keepalive settings |
| Ansible Playbook | Runs `provision.yml --limit {env}` against the target host |
| Deployment Report | Parses PLAY RECAP into a summary table with collapsible full log |
| Disconnect | Tears down the WireGuard tunnel (always runs) |

<br>

### Updates (Scheduled)

**File:** `.github/workflows/updates.yml`
**Trigger:** Scheduled every Tuesday at 02:00 UTC (`cron: '0 2 * * 2'`), or manual dispatch.

Runs the `updates.yml` playbook against the **test** environment to apply OS package updates safely.

| Step | Description |
|------|-------------|
| Azure Login | Authenticates to Azure for KeyVault access |
| Get Secrets | Pulls secrets from Azure KeyVault into the runner environment |
| Replace Tokens | Substitutes `#{TOKEN}#` placeholders in config files |
| WireGuard VPN | Connects to home network via WireGuard tunnel |
| Add Routes | Adds a route to the target host over WireGuard |
| SSH Setup | Configures SSH keys and pinned host fingerprints |
| Ansible Playbook | Runs `updates.yml --limit {env}` to apply updates |


<br>
<br>

## 🤐 Secrets & Variables
<br>

To avoid storing secrets in any files I use a combination of environment variables GitHub Secrets, and Azure KeyVault.

Secrets are never stored in the repository. The workflow uses a two-layer approach:

1. **GitHub Environment Secrets** — SSH keys, WireGuard config, host fingerprints
2. **Azure KeyVault** — All application secrets (Samba passwords, SSH public keys, etc.)

Secrets are injected at deploy time using token replacement:
- Config files contain `#{TOKEN}#` placeholders
- The [Replace Tokens](https://github.com/marketplace/actions/replace-tokens) action substitutes them with matching environment variables sourced from KeyVault

<br>
<br>

## 🔒 Security
<br>

- All GitHub Actions are **pinned to commit SHAs** to prevent supply-chain attacks
- [Dependabot](https://docs.github.com/en/code-security/dependabot) monitors for new versions weekly
- SSH connections use **pinned host fingerprints** (no trust-on-first-use)
- The runner connects via **WireGuard VPN** — no ports exposed to the internet
- Azure SPN credentials use scoped access to a single KeyVault

<br>
<br>


## 📎 Related Repos

| Repo | Purpose |
|------|---------|
| [nas-docker](https://github.com/osotechie/nas-docker) | Docker Compose stacks deployed on the NAS |
