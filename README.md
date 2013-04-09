# Compiler Project

A project for my EECE 6083: Compiler Theory class.

## Usage
* Install [Python 2.7](http://python.org/download/) if it is not already installed on your system.
* You can see a sample of the output of each stage of the compiler by calling running any module from the command line.
* To run the compiler, execute the following command from the root compiler folder:
```
python main.py /path/to/source.src
```
* The full set of options for the compiler are:

        usage: main.py [-h] [-o OUTPUT] [-O {0,1,2}] [-R] [-c] [-v] filename
        
        Compile a source file into a c file and an executable.
        
        positional arguments:
          filename              the file to parse
        
        optional arguments:
          -h, --help            show this help message and exit
          -o OUTPUT, --output OUTPUT
                                name of the executable that will be produced
          -O {0,1,2}            run a set of optimizations (0=no optimization,
                                1=minimal optimization, 2=advanced optimization)
          -R, --no-runtime      do not link the runtime IO functions
          -c                    only parse and assemble the code to C, do not run gcc
          -v, --verbose-assembly
                                add comments to the generated code


## Testing
Unit Tests for the compiler are written using the [nose](https://github.com/nose-devs/nose) testing framework.
If you have nose installed on your system, you can run `nosetests` from the `compiler` directory to run the tests.
The tests have 100% code coverage of the scanner, parser, and type checker, and high coverage of the optimizer, as reported by the [coverage](http://pypi.python.org/pypi/coverage) package.

## Author
AJ Alt
