# fprc
We will need an active iRODS server running on localhost at port 1247.
Default install is fine.

Change directory to the repository root (or one level above fprc/).

To run demos:
```bash
itouch testobj.dat
imeta set -d testobj.dat attr value units
for script python3/demo*py:
do
  command ${script}
done
```

To run tests  installation
is needed:

```bash
sudo apt install python3-pytest python3-venv
python -m venv py3-fprc
source py3-fprc/bin/activate
pip install fprc/
python -m pytest fprc/
```
