# check_librespeed.py   
A monitoring script compatible with nagios/icinga2 to check the internetspeed of the system.
This script depends on the [librespeed-cli](https://github.com/librespeed/speedtest-cli) provided from [librespeed](https://github.com/librespeed).

### Installation
librespeed-cli [releases](https://github.com/librespeed/speedtest-cli/releases).
Follow below instructions.
```
git clone https://gitlab.com/Guentha/check_librespeed.git
sudo chown -R root.root check_librespeed
cd check_librespeed
wget https://github.com/librespeed/speedtest-cli/releases/download/<version>/librespeed-cli_<version>_<os>_<cpu_architecture>.tar.gz librespeed-cli.tar.gz
mkdir Librespeed-cli
gunzip librespeed-cli.tar.gz
tar -xvf librespeed-cli.tar -C Librespeed-cli/
sudo chown -R root.root Librespeed-cli
cd ..
# For Centos/Redhat
mv check_librespeed /usr/lib64/nagios/plugins/
# For Ubuntu/Debian
mv check_librespeed /usr/lib/nagios/plugins/
```

### Usage
```
usage: check_librespeed.py [options]

Nagios/Icinga2 Monitoring script for checking the internet speed.Values
returned in bit/s. Speedtest are performed via HTTPS.

optional arguments:
  -h, --help            show this help message and exit
  -w <download>;<upload>;<ping>;<jitter>, --warning <download>;<upload>;<ping>;<jitter>
                        The warning thresholds. Usage:
                        <download>;<upload>;<ping>;<jitter>Zero disables the
                        check for the given type. Default: 50;20;75;0
  -c <download>;<upload>;<ping>;<jitter>, --critical <download>;<upload>;<ping>;<jitter>
                        The critical thresholds. Usage:
                        <download>;<upload>;<ping>;<jitter>. Zero disables the
                        check for the given type. Default: 25;10;100;0
  --perfdata            Create performance data. Default: False
  -s <integer>, --server <integer>
                        Which server to use for the speedtest. Provide the
                        number listed with the argument '--list'. Default
                        choose a random one.
  -l, --list            List available servers for the speedtest. Default:
                        False
  --mebibytes           Use 1024 bytes as 1 kilobyte instead of 1000. Default:
                        False
```

### Author
* Guentha Unknown 