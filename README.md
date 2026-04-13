## CSC 435 Distributed Systems I  
**Jarvis College of Computing and Digital Media - DePaul University**

This repository contains the source code and files for the autograder programs.

### Software Requirements

This autograder is designed to run on a standard Ubuntu 24.04 LTS Server Edition OS. You will need to use **CMake** or **Maven** (to build the programs), **GCC 14** or **OpenJDK 21** (to compile and link the programs), and **Python 3.14** (to run the testing script).

To install the necessary software packages, including Python 3.14 from the deadsnakes PPA, open a terminal and run the following commands:

```shell
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.14 build-essential cmake g++-14 gcc-14 maven openjdk-21-jdk
sudo update-alternatives --remove-all gcc
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 130
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-14 140
sudo update-alternatives --remove-all g++
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-13 130
sudo update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-14 140
```