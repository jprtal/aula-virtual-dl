<h1 align="center">aula-virtual-dl</h1>

<p align="center">Tooling that fully <b>automates</b> the downloading of the content from your <a href="https://www.aulavirtual.urjc.es">URJC Aula Virtual</a> courses. :pencil2:<p>

## Usage
```elm
python3 aula_virtual.py
```
Optional arguments:
```
aula_virtual.py [-u username] [-r directory] [-s size] [-c coursename] [-o]

-u --user       user
-r --route      location to download
-s --size       maximum file size in MB
-c --course     course name
-o --overwrite  overwrite existing files
```

## Requirements
Depending on your system, make sure to use `python3` and `pip3`.

#### Windows
Install python [release](https://www.python.org/ftp/python/3.8.2/python-3.8.2-amd64.exe) for Windows. During installation make sure to check `Add Python 3.X to PATH`.
```
pip install -r requirements.txt
```
#### GNU/Linux
```zsh
sudo apt install python3 python3-pip
pip install -r requirements.txt
```

#### macOS
```zsh
xcode-select --install
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
brew install python3
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
pip3 install --user -r requirements.txt
```
If you face `SSL: CERTIFICATE_VERIFY_FAILED` error you might solve it by installing `certifi`:
```
pip3 install --upgrade certifi
```

## License
[MIT license](LICENSE).
