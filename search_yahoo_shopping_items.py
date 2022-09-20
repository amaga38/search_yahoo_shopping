import sys
import argparse
import subprocess


def main():
    args = len(sys.argv)
    print(args, sys.argv)
    argv = ['python', 'search_yahoo_shopping.py', '--only-search-item']
    argv += sys.argv[1:]
    r = subprocess.run(argv)
    return 0


if __name__ == '__main__':
    exit(main())
