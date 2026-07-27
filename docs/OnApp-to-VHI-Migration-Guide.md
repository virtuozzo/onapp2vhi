# OnApp to Virtuozzo Hybrid Infrastructure (VHI) Migration Guide

Migrate virtual servers and related tenant resources from OnApp to Virtuozzo Hybrid Infrastructure using the **onapp2vhi** CLI.

**Audience:** cloud operators / administrators with access to OnApp Control Panel (CP) and VHI.

---

## 1. Process overview

Migration is orchestrated by a single command: `onapp2vhi migrate`.

For each selected OnApp user, the tool:

1. Creates (or reuses) a VHI project and user, maps quotas, and migrates SSH keys.
2. Prepares each virtual server (VS) for VHI (bootloader / drivers, optional cloud-init and Virtuozzo guest tools).
3. Transfers disks and creates the equivalent VM on VHI.
4. Suspends the source VS on OnApp after a successful transfer.
5. Writes migration logs (including generated credentials).

### Migration modes

Mode is chosen automatically from the VS power state:

| Source VS state | Mode | Result on VHI |
|-----------------|------|---------------|
| **Stopped** | Cold (offline) — disk copy via NBD / `qemu-img` | VM **shut off** |
| **Running**, SSH reachable, hot migrate allowed | Live (hot) — `virsh migrate --live --copy-storage-all` | VM **active** |

- To force **cold** migration: shut down the VS on OnApp before running the tool.
- To use **live** migration: leave the VS running, ensure SSH access and that hot migrate is allowed.

### What is migrated

- Users and projects (with quota mapping from OnApp buckets)
- SSH keys
- Virtual servers (CPU/RAM flavor, disks, NICs, hostname)
- Networks (match an existing VHI network, or create an IPv4 virtual network when allowed)
- Firewall rules → VHI security groups (primary NIC)

### What is not migrated

Backups, CDN, edge servers, load balancers, and other non-VS OnApp services are out of scope.

---

## 2. Requirements

### Access and connectivity

- Operator host with SSH access to **OnApp** (CP, hypervisors, backup servers) and **VHI** (controller / CP, compute nodes).
- Recommended: run as the `onapp` user on the **OnApp Control Panel**.
- OnApp SSH key available on **all VHI nodes**.
- Shared **migration network** between OnApp and VHI hypervisors (`migration_network_id` in config).
- Python 3 virtual environment for installing and running `onapp2vhi`.

### VHI prerequisites

- Target **domain**, **storage policy**, and placeholder images (`linux_image`, `windows_image`) configured.
- Secondary NIC security group created in the target project (`vhi_secondary_security_group`).
- If using `--project` or `--flavor`, the project / flavor must **already exist** on VHI.
- Temporary: disable port security on networks used for migration; re-enable after migration completes.

### Guest prerequisites

- **Live path:** guest SSH reachable (default port 22, or `--vm-ssh-port`).
- **Linux:** bootloader compatible with VHI (tool installs/adjusts GRUB where needed).
- **Windows:** VirtIO / driver preparation performed by the tool.
- **Debian 9:** install `grub2` and reboot **before** migration (see Known issues).

### Configuration

Create `~/.config/onapp2vhi/config.ini` (or `./config.ini`) with OnApp API credentials, VHI endpoints, images, domain/project, storage policy, `migration_network_id`, secondary security group, and SSH key path.

Generate a template:

```bash
onapp2vhi --generate-config
```

Edit interactively:

```bash
onapp2vhi-config
```

---

## 3. Limitations

| Limitation | Behavior |
|------------|----------|
| Suspended VS | Skipped |
| VS marked VIP | Skipped |
| VS already present on VHI (same hostname in target domain) | Skipped |
| No primary IP | Migration aborted for that VS |
| Conflicting IP/MAC already on VHI | Migration aborted |
| Running VS without SSH | Live path fails; stop the VS and use cold migration (or fix SSH) |
| IPv6-only networks | Tool does not auto-create; preconfigure on VHI or remove IPv6 addresses |
| IPv6 as primary on Windows NIC | Not supported |
| Full-cloud migrate (`onapp2vhi migrate` with no filters) | Supported but **not recommended** |
| Skipping cloud-init / vz-guest-tools | Allowed, but correct post-migration operation is not guaranteed |
| ISO/OVA-built guests | GRUB / cloud-init install steps may be skipped |

Migrate **user by user** (or user + specific VMs). Avoid migrating the entire cloud in one run.

---

## 4. Step-by-step execution

### Step 1 — Prepare SSH

On OnApp CP:

```bash
su - onapp
export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket
ssh-add -L   # if this fails, restart the onapp service
```

Ensure the OnApp SSH public key is installed on all VHI nodes.

### Step 2 — Install the tool

```bash
virtualenv -p python3 ~/myenv/
source ~/myenv/bin/activate
pip install --upgrade pip
pip install git+ssh://git@bitbucket.org/virtuozzocore/onapp2vhi.git@v1.0.0
```

Use the release tag or package source provided for your deployment.

### Step 3 — Configure

1. Create and fill `~/.config/onapp2vhi/config.ini`.
2. Create the VHI service user:

   ```bash
   onapp2vhi create_service_user
   ```

3. On the VHI controller, load admin credentials and temporarily disable port security on migration networks:

   ```bash
   source /etc/kolla/admin-openrc.sh
   openstack --insecure network set --disable-port-security <network_id>
   ```

### Step 4 — Inventory

```bash
onapp2vhi list-onapp-users --find="id=7"
onapp2vhi list-onapp-vms --find="user_id=7" \
  --props=identifier,hostname,memory,cpus,user_id,template_label,total_disk_size
```

Decide cold vs live per VS (power state). Unsuspend VIP-marked or suspended VMs only if you intend to migrate them after clearing those flags.

### Step 5 — Migrate

Recommended patterns:

```bash
# All VSs for one user
onapp2vhi migrate --user=7

# Specific VSs
onapp2vhi migrate --user=7 --vm=sydarelogizozd,lidqtfwggohyzk

# Into a pre-created VHI project
onapp2vhi migrate --user=7 --project=my_project
```

Useful options:

| Option | Purpose |
|--------|---------|
| `--vm-ssh-port` | Guest SSH port (default 22) |
| `--storage_policy` | VHI storage policy |
| `--placement` | VHI placement |
| `--flavor` | Existing VHI flavor (default: derive from OnApp VS) |
| `--network` | Target VHI network name or ID |
| `--hotplug` | Enable CPU/RAM hot plug on VHI VM |
| `--cloud_init_install=false` | Skip cloud-init install |
| `--vz_guest_tools_install=false` | Skip Virtuozzo guest tools |
| `--strict-ip-pool-match` | Require IP pool range match |
| `--no-network-create` | Do not create new virtual networks |

Debug logging:

```bash
export loglevel=debug
```

### Step 6 — Verify and wrap up

1. Check logs under `~/onapp2vhi/migration_logs/` (or the path from `--log-output-path`): full log and per-user result files with credentials.
2. Confirm VMs on VHI (cold → shut off; live → active), networks, and security groups.
3. Re-enable port security on VHI networks:

   ```bash
   openstack --insecure network set --enable-port-security <network_id>
   ```

4. If `vinfra` reports stale cache errors:

   ```bash
   rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*
   ```

---

## 5. Known issues

**Debian 9 (Stretch):** install `grub2` before migration. Archive repositories may be required:

```text
deb http://archive.debian.org/debian/ stretch main contrib non-free
deb http://archive.debian.org/debian/ stretch-proposed-updates main contrib non-free
deb http://archive.debian.org/debian-security stretch/updates main contrib non-free
```

```bash
apt update && apt install grub2
reboot
```

---

## 6. Quick reference

```bash
onapp2vhi --help
onapp2vhi --generate-config
onapp2vhi-config
onapp2vhi create_service_user
onapp2vhi list-onapp-users
onapp2vhi list-onapp-vms
onapp2vhi migrate --user=<id> [--vm=<id1,id2>] [options...]
```

---

*Product: onapp2vhi — OnApp to Virtuozzo Hybrid Infrastructure migration tool.*  
*For support and release packages, contact your Virtuozzo representative.*
