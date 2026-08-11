# OnApp to Virtuozzo Infrastructure (V/IS) Migration Guide

Migrate virtual servers and related tenant resources from Virtuozzo OnApp to Virtuozzo Infrastructure (V/IS) using the **onapp2vhi** CLI.

**Audience:** cloud operators / administrators with access to OnApp Control Panel (CP) and V/IS.

---

## 1. Process overview

Migration is orchestrated by a single command: `onapp2vhi migrate`.

For each selected OnApp user, the tool:

1. Creates (or reuses) a V/IS project and user, maps quotas, and migrates SSH keys.
2. **OS conversion** — prepares the guest for V/IS (GRUB/UUID, fstab if needed, optional cloud-init / cloudbase-init and Virtuozzo guest tools, post-migration scripts).
3. Transfers disks and creates the equivalent VM on V/IS.
4. **Cutover** — suspends the source VS on OnApp; for live migration, finalizes the V/IS VM and applies prepared scripts.
5. Writes migration logs (including generated credentials).

### Migration modes

Mode is chosen automatically from the VS power state:

| Source VS state | Mode | Transfer | Result on V/IS |
|-----------------|------|----------|----------------|
| **Stopped** | Cold (offline) | `qemu-img convert` from NBD on OnApp HV → V/IS node | VM **shut off** (start and verify manually) |
| **Running**, SSH reachable, hot migrate allowed | Live (hot) | `virsh migrate --live --copy-storage-all` | VM **active** after cutover |

- To force **cold**: shut down the VS on OnApp before running the tool.
- To use **live**: leave the VS running, ensure SSH access and that hot migrate is allowed.
- Live migration requires **similar CPU architecture** on source and target hypervisors (Intel→Intel or AMD→AMD).

### What is migrated

- Users and projects (with quota mapping from OnApp buckets)
- SSH keys
- Virtual servers (CPU/RAM flavor, disks, NICs, hostname)
- Networks (match an existing V/IS network, or create an IPv4 virtual network when allowed)
- Firewall rules → V/IS security groups (primary NIC; complex rules may not map fully)

### What is not migrated

Load balancers, backups, CDN, edge servers, and other non-VS OnApp services.

---

## 2. Platform and capacity planning

Before tooling:

1. Analyze source OnApp architecture and capacity.
2. Plan the destination Virtuozzo Infrastructure cluster (or validate an existing one).
3. Deploy and configure destination resources (domains, networks, IPs, images, storage policies).
4. Deploy and configure `onapp2vhi`.
5. Migrate user by user (or VM by VM); keep a direct support channel for assisted runs.

**Inventory (recommended before migrate):**

| VM name | OS | Disk (GB) | IP type (static/DHCP) | Target network | Target project | Storage policy | Window |

Collect Name, OS version, IP addresses, and disk storage type for every VS.

---

## 3. Requirements

### Supported platforms

- **OnApp:** version **6.0+**
- **Source hypervisor OS:** **CentOS 7** strongly recommended
- **Guest OS:** only [OnApp-supported guest operating systems](https://docs.virtuozzo.com/) for your OnApp release (e.g. OnApp 7.2 supported guest OS list)
- **Virtuozzo Infrastructure (V/IS):** cluster deployed and ready for VM onboarding (new), or health-check and performance check passed (existing)

### Migration network

Critical for both cold and live paths:

- Dedicated L2/L3 path (usually a **VLAN**) between OnApp hypervisors (at least one) and V/IS compute nodes
- **Not firewalled** between clusters
- Bandwidth: **100 Mbps minimum**, **10 Gbps recommended**
- Configured as `migration_network_id` on V/IS and reachable from OnApp HVs
- **Cold path:** V/IS nodes must reach OnApp nodes (**reverse** connectivity over the migration network) to attach to NBD

### Access and connectivity

- Operator host with SSH to **OnApp** (CP, hypervisors, backup servers) and **V/IS** (controller / CP, compute nodes)
- Recommended: run as the `onapp` user on the **OnApp Control Panel**
- OnApp SSH key installed on **all V/IS nodes**
- Python 3 virtual environment for `onapp2vhi`

### Prepare OnApp

- Inventory all VSs (see table above)
- Confirm guest OS is supported
- Confirm migrating **IPs are free/available** on the V/IS side for customer networks
- **Linux:** `grub2` installed (see Known issues for Debian 9)
- **Live path:** SSH into the guest works (default key; custom port supported via `--vm-ssh-port`)
- Virtuozzo guest tools installed/updated where possible (the tool can install them; optional flag to skip)
- Migration network open from V/IS toward OnApp HVs

### Prepare Virtuozzo Infrastructure (destination cloud)

This guide does **not** replace Virtuozzo Infrastructure cluster installation docs. For migration readiness:

- Target **domains** created
- **Customer networks** created; required IPs available (match OnApp addressing as planned)
- **Migration network** present on nodes and usable
- Default **Linux** and **Windows** images configured — typically **no UEFI**, disk bus **virtio**
- Storage policy (and optional placement) decided
- Secondary NIC security group exists (`vhi_secondary_security_group` in config)
- Projects, flavors, and users can be created by the tool, or pre-created (`--project`, `--flavor` must already exist if you pass them)
- Temporary: **disable port security** on networks used during migration; re-enable after

### Configuration

Create `~/.config/onapp2vhi/config.ini` (or `./config.ini`) with OnApp API credentials, V/IS endpoints, images, domain/project, storage policy, `migration_network_id`, secondary security group, and SSH key path.

```bash
onapp2vhi --generate-config
onapp2vhi-config
```

---

## 4. Limitations

| Limitation | Behavior |
|------------|----------|
| Unsupported guest OS | Do not migrate until OS is supported |
| Suspended VS | Skipped |
| VS marked VIP | Skipped |
| VS already present on V/IS (same hostname in target domain) | Skipped |
| No primary IP | Migration aborted for that VS |
| Conflicting IP/MAC already on V/IS | Migration aborted |
| Running VS without SSH | Live path fails; stop the VS and use cold migration (or fix SSH) |
| Live: dissimilar CPU (Intel↔AMD) | Not suitable for hot migration |
| IPv6-only networks | Tool does not auto-create; preconfigure on V/IS or remove IPv6 addresses |
| IPv6 as primary on Windows NIC | Not supported |
| Load balancers / backups | Not migrated |
| Complex firewall rules | May not migrate completely |
| Full-cloud migrate (`onapp2vhi migrate` with no filters) | Supported but **not recommended** |
| Skipping cloud-init / vz-guest-tools | Allowed, but correct post-migration operation is not guaranteed |
| ISO/OVA-built guests | GRUB / cloud-init install steps may be skipped |

Migrate **user by user** (or user + specific VMs). Avoid evacuating the entire cloud in one run unless planned as assisted mass migration.

---

## 5. Step-by-step execution

### Step 1 — Prepare SSH

On OnApp CP:

```bash
su - onapp
export SSH_AUTH_SOCK=/onapp/interface/tmp/onapp-ssh-agent.socket
ssh-add -L   # if this fails, restart the onapp service
```

Ensure the OnApp SSH public key is installed on all V/IS nodes.

### Step 2 — Install the tool

```bash
virtualenv -p python3 ~/myenv/
source ~/myenv/bin/activate
pip install --upgrade pip
pip install git+ssh://git@github.com/virtuozzo/onapp2vhi.git@o2v-ps
```

Install from the `o2v-ps` branch on GitHub (`virtuozzo/onapp2vhi`).

### Step 3 — Configure

1. Create and fill `~/.config/onapp2vhi/config.ini`.
2. Create the V/IS service user:

   ```bash
   onapp2vhi create_service_user
   ```

3. On the V/IS controller, load admin credentials and temporarily disable port security on migration networks:

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

Decide cold vs live per VS (power state + CPU architecture + SSH). Clear suspended/VIP flags only if you intend to migrate those VSs.

### Step 5 — Migrate

```bash
# All VSs for one user
onapp2vhi migrate --user=7

# Specific VSs
onapp2vhi migrate --user=7 --vm=sydarelogizozd,lidqtfwggohyzk

# Into a pre-created V/IS project
onapp2vhi migrate --user=7 --project=my_project
```

| Option | Purpose |
|--------|---------|
| `--vm-ssh-port` | Guest SSH port (default 22) |
| `--storage_policy` | V/IS storage policy |
| `--placement` | V/IS placement |
| `--flavor` | Existing V/IS flavor (default: derive from OnApp VS) |
| `--network` | Target V/IS network name or ID |
| `--hotplug` | Enable CPU/RAM hot plug on V/IS VM |
| `--cloud_init_install=false` | Skip cloud-init install |
| `--vz_guest_tools_install=false` | Skip Virtuozzo guest tools |
| `--strict-ip-pool-match` | Require IP pool range match |
| `--no-network-create` | Do not create new virtual networks |

```bash
export loglevel=debug
```

### Step 6 — Verify and wrap up

1. Check logs under `~/onapp2vhi/migration_logs/` (or `--log-output-path`): full log and per-user result files with credentials.
2. Confirm VMs on V/IS (cold → start and verify; live → already active), networks, and security groups.
3. Re-enable port security:

   ```bash
   openstack --insecure network set --enable-port-security <network_id>
   ```

4. If `vinfra` reports stale cache errors:

   ```bash
   rm -f ~/.vinfra/backend-api.svc.vstoragedomain/*
   ```

---

## 6. Known issues

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

## 7. Quick reference

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

*Product: onapp2vhi — OnApp to Virtuozzo Infrastructure (V/IS) migration tool.*  
*For assisted migration scope and release packages, contact Virtuozzo Professional Services.*
