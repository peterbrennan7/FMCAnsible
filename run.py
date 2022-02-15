#!/usr/bin/env python
import sys
from ansible.cli.playbook import PlaybookCLI

def main():
    cli = PlaybookCLI(sys.argv)
    cli.run()

if __name__ == "__main__":
    main()