# Compiler Project

A project for my EECE 6083: Compiler Theory class.

## Quick Start
* Install [Python 2.7](http://python.org/download/) if it is not already installed on your system.
* You can see a sample of the scanner output by running the following from the root `compiler` directory:
```
python src/scanner.py test/test_program.src
```
* You can see a sample of the parser output by running either of the following:
```
python src/parser.py test/test_program.src
```
```
python src/parser.py -e "1 + 2 * 3 / (4 + 5) == true"
```
* You can see a sample of the type checking by running the following:
```
python src/typechecker.py test/test_program.src
```
* You can see a sample of the optimizer by running the following:
```
python src/optimizer.py test/test_program.src
```
* You can see a sample of the code generator by running the following:
```
python src/codegenerator.py test/test_program.src
```


## Testing
Unit Tests for the compiler are written using the [nose](https://github.com/nose-devs/nose) testing framework.
If you have nose installed on your system, you can run `nosetests` from the `compiler` directory to run the tests.
The tests have 100% code coverage of the scanner, parser, and type checker, and high coverage of the optimizer, as reported by the [coverage](http://pypi.python.org/pypi/coverage) package.

## Author
AJ Alt
