def main():
    import argparse
    import subprocess
    import os
    import sys

    from ececompiler import scanner
    from ececompiler import parser
    from ececompiler import typechecker
    from ececompiler import optimizer
    from ececompiler import codegenerator

    argparser = argparse.ArgumentParser(description=
                                'Compile a source file into a c file and an executable.')
    
    argparser.add_argument('filename', help='the file to parse')
    argparser.add_argument('-o', '--output', default='a.out',
                           help='name of the executable that will be produced')
    argparser.add_argument('-O', type=int, choices=xrange(3), default=0,
                           help='run a set of optimizations '
                           '(0=no optimization, 1=minimal optimization, '
                           '2=advanced optimization)')
    argparser.add_argument('-R', '--no-runtime', action='store_true',
                            help='do not link the runtime IO functions')
    argparser.add_argument('-c', action='store_true',
                            help='only parse and assemble the code to C, do not run gcc')
    argparser.add_argument('-v', '--verbose-assembly', action='store_true',
                           help='Add comments to the generated code')
    args = argparser.parse_args()
    
    asm_filename = os.path.splitext(os.path.basename(args.filename))[0].strip() + '.c'
    try:
        ast = parser.parse_tokens(scanner.tokenize_file(args.filename),
                                  include_runtime=(not args.no_runtime))
    except parser.ParseFailedError:
        pass
    else:
        if typechecker.tree_is_valid(ast):
            optimizer.optimize_tree(ast, args.O)
            
            with open(asm_filename, 'w') as f:
                codegenerator.output_code(ast, f, args.verbose_assembly)
                
            if not args.c:
                sys.exit(subprocess.call(['gcc', '-m32', '-o', args.output, 'runtime.c', asm_filename]))
    sys.exit(1)
        
if __name__ == '__main__':
    main()