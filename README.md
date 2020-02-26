# aula-virtual-dl
This small python script allows you to download all the content from your [URJC Aula Virtual](https://www.aulavirtual.urjc.es) courses (.pdf, .docx, .pptx, etc.). It works as a crawler, checking the site for files as if it was you with your browser.

## Usage
Download the repository as zip, clone it with git, or just use curl to get only the script. On GNU/Linux or MacOS:
```
git clone https://github.com/jprtal/aula-virtual-dl.git
cd aula-virtual-dl
pip3 install --user -r requirements.txt
python3 aula_virtual.py
```
Optional arguments:
```
-u --user    user
-r --route   location to download
-s --size    maximum file size in MB
-c --course  course name
```

## Requirements
Python version 3.7 or above is required to run the script. Also, you'll need two libraries: `mechanize` and `beautifoulsoup`.

Most of GNU/Linux distributions call the python package as "python3". To install dependencies on Debian based GNU/Linux distros (Ubuntu, Linux Mint, ...):
```
sudo apt-get install python3 python3-pip
pip install -r requirements.txt
```
To install dependencies on MacOS:
```
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
This script is under [MIT license](https://github.com/jprtal/aula-virtual-dl/blob/master/LICENSE).
