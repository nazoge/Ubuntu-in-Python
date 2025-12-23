import os
import sys
import subprocess
import urllib.request
import tarfile
import stat
import shutil

ROOTFS_DIR = "./ubuntu_rootfs"
PROOT_BIN = "./proot"
PROOT_URL = "https://github.com/ysdragon/proot-static/releases/download/v5.4.0/proot-x86_64-static"
UBUNTU_URL = "https://cloud-images.ubuntu.com/minimal/releases/jammy/release/ubuntu-22.04-minimal-cloudimg-amd64-root.tar.xz"

def on_rm_error(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        print(f"Warning: Failed to force remove {path}: {e}")

def download_file(url, dest_path):
    if os.path.exists(dest_path):
        print(f"{dest_path} already exists.")
        return
    print(f"Downloading: {url} ...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(dest_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print("Download complete!")
    except Exception as e:
        print(f"Download error: {e}")
        sys.exit(1)

def setup_proot():
    download_file(PROOT_URL, PROOT_BIN)
    try:
        st = os.stat(PROOT_BIN)
        os.chmod(PROOT_BIN, st.st_mode | stat.S_IEXEC)
        print("Granted execution permissions to PRoot.")
    except Exception as e:
        print(f"Warning (chmod): {e}")

def setup_rootfs():
    if os.path.exists(ROOTFS_DIR) and not os.path.exists(os.path.join(ROOTFS_DIR, "etc")):
        print("Broken installation detected. Removing and reinstalling...")
        shutil.rmtree(ROOTFS_DIR, onexc=on_rm_error)

    if not os.path.exists(ROOTFS_DIR):
        os.makedirs(ROOTFS_DIR)
    
    if os.path.exists(os.path.join(ROOTFS_DIR, "bin", "bash")) and os.path.exists(os.path.join(ROOTFS_DIR, "etc")):
        print("Ubuntu is already installed.")
    else:
        tar_path = "rootfs.tar.xz"
        download_file(UBUNTU_URL, tar_path)
        print("Extracting Ubuntu...")
        try:
            with tarfile.open(tar_path, "r:xz") as tar:
                members = []
                for member in tar.getmembers():
                    if member.ischr() or member.isblk():
                        continue
                    members.append(member)
                tar.extractall(path=ROOTFS_DIR, members=members)
            print("Extraction complete!")
            if os.path.exists(tar_path): os.remove(tar_path)
        except Exception as e:
            print(f"Extraction error: {e}")
            if os.path.exists(ROOTFS_DIR): 
                shutil.rmtree(ROOTFS_DIR, onexc=on_rm_error)
            sys.exit(1)

    print("Configuring DNS...")
    resolv_dir = os.path.join(ROOTFS_DIR, "etc")
    if not os.path.exists(resolv_dir):
        os.makedirs(resolv_dir)
        
    resolv_conf = os.path.join(resolv_dir, "resolv.conf")
    try:
        with open(resolv_conf, "w") as f:
            f.write("nameserver 1.1.1.1\n")
            f.write("nameserver 8.8.8.8\n")
        print("DNS configuration updated.")
    except Exception as e:
        print(f"Warning: Failed to update DNS: {e}")

def run_ubuntu():
    print("Starting Ubuntu...")
    print("--- Terminal Mode ---")
    
    cmd = [
        PROOT_BIN,
        "--rootfs=" + ROOTFS_DIR,
        "-0",
        "-w", "/root",
        "-b", "/dev",
        "-b", "/sys",
        "-b", "/proc",
        "-b", "/etc/resolv.conf",
        "/bin/bash"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Process exited: {e}")

if __name__ == "__main__":
    setup_proot()
    setup_rootfs()
    run_ubuntu()
