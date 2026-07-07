#!/usr/bin/env python3

from argparse import ArgumentParser
from os import path, walk, lstat
from pathlib import Path
from re import compile, match
from stat import S_ISREG
from tqdm import tqdm
from subprocess import Popen, PIPE

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR / "data"


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        "firmware_directory"
    )
    parser.add_argument(
        "-o",
        "--output",
        help    = "Optional name of the file to store results - defaults to " +\
               "\"firmwalker.txt\"",
        default = "firmwalker.txt"
    )
    return vars(parser.parse_args())


class Firmwalker():
    def __init__(self, firmware_directory, output_file):
        if not path.isdir(firmware_directory):
            print("[!] Please choose a valid directory")
            exit(-1)
        self.directory   = firmware_directory
        self.output_file = output_file
        self.filelisting = []
        self.dfd         = {}
        self.located     = {}
        self.separator   = "#"*79
        self.subline     = '-'*21

        self.output      = ""

        self.filelisting = self.get_full_file_listing(self.directory)
        self.get_data_files()
        self.iter_dfds()
        self.write_results()


    def get_full_file_listing(self, directory):
        directory = path.abspath(directory)

        returnable = []
        for root, dirs, files in walk(directory, followlinks=False):
            for name in files:
                full = path.join(root, name)
                try:
                    if S_ISREG(lstat(full).st_mode):
                        returnable.append(full)
                except OSError:
                    continue

        return returnable


    def get_data_files(self):
        tmp_dfd = self.get_full_file_listing(str(DATA_DIR))
        for f in tmp_dfd:
            with open(f, 'r') as fptr:
                tmp_content = fptr.read()
            self.dfd[f.split("/")[-1]] = tmp_content.splitlines()

        return


    def not_searching_patterns(self, d, tmp_filelisting):
        for st in self.dfd[d]:
            if st.startswith("*") or st.endswith("*"):
                if "." in st: st = st.replace(".", "\\.")
                if st.startswith("*"): st = f".{st}"
                if st.endswith("*")  : st = f"{st}."
                search_term = compile(st)
                matches = [
                    self.filelisting[idx]
                    for idx, name in enumerate(tmp_filelisting)
                    if search_term.match(name)
                ]
                if matches:
                    if d not in self.located: self.located[d] = {}
                    self.located[d][st] = matches

            else:
                matches = [
                    self.filelisting[idx]
                    for idx, name in enumerate(tmp_filelisting)
                    if name == st
                ]
                if matches:
                    if d not in self.located: self.located[d] = {}
                    self.located[d][st] = matches
        return


    def searching_patterns(self, d, tmp_filelisting):
        patterns = [
            (str(st), bytes(str(st), "utf-8"))
            for st in self.dfd[d] if str(st).strip()
        ]
        for st, _ in patterns:
            op = f"\tSearching for: {st}\n"
            self.store_results(op)

        for file in tqdm(self.filelisting):
            try:
                with open(file, 'rb') as fptr:
                    content = fptr.read()
            except OSError:
                continue
            for st, st_bytes in patterns:
                if st_bytes in content:
                    if d not in self.located: self.located[d] = {}
                    if st not in self.located[d]: self.located[d][st] = []
                    self.located[d][st].append(file)
        return


    def print_results(self, dfd):
        for found in self.located[dfd]:
            if type(self.located[dfd][found]) == str:
                op = f"Found: {self.located[dfd][found]}"
                self.store_results(op)
            else:
                tmp = ''
                for f in self.located[dfd][found]:
                    if tmp == found:
                        op = f
                    else:
                        tmp = found
                        op = f"{self.subline} {found} {self.subline}\n"
                        op += f
                    self.store_results(op)
        return

    def grep(self, d, tmp_filelisting):
        cmd = ["/bin/bash", str(DATA_DIR / d), self.directory]
        process = Popen(cmd, stdout=PIPE, stderr=PIPE)
        out, err = process.communicate()
        out = out.decode("utf-8")
        self.store_results(out)


    def store_results(self, op):
        self.output += f"{op}\n"
        print(op)


    def iter_dfds(self):
        tmp_filelisting = [f.split('/')[-1] for f in self.filelisting]
        for d in self.dfd:
            op = f"[+] Searching {d}"
            self.store_results(op)
            if d != "patterns" and not d.endswith("_regex"):
                self.not_searching_patterns(d, tmp_filelisting)
            elif d == "patterns":
                self.searching_patterns(d, tmp_filelisting)
            elif d.endswith("_regex"):
                self.grep(d, tmp_filelisting)

            if d in self.located:
                self.print_results(d)
            self.store_results(self.separator)


    def write_results(self):
        while path.isfile(self.output_file):
            head, tail = path.split(self.output_file)
            self.output_file = path.join(head, f"_{tail}")
        with open(self.output_file, 'w') as fptr:
            fptr.write(self.output)
        print(f"[+] Results written to {self.output_file}")

def main():
    args = get_args()
    firmwalker = Firmwalker(
        args["firmware_directory"],
        args["output"],
    )
    return


if __name__ == "__main__":
    exit(main())
