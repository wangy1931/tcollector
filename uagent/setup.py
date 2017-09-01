# encoding=utf-8

import os
from shutil import copy


class Setup:
    def __init__(self):
        self.package_path = os.path.dirname(os.path.abspath(__file__))
        self.struct_file = open(self.package_path + "/struct.txt", "r")

    def setfile(self):
        for line in self.struct_file:
            filename, path = line.split(" ")
            src = os.path.join(self.package_path, filename)
            des = path
            copy(src, des)


if __name__ == "__main__":
    s = Setup()
    s.setfile()
