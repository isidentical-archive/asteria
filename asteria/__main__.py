import sys

from asteria import asteria


def main(argv=None):
    console = asteria.AsteriaConsole(locals=vars(asteria))
    console.interact()


if __name__ == "__main__":
    main(sys.argv[1:])
