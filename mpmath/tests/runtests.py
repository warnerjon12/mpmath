#!/usr/bin/env python

"""
python runtests.py -py
  Use py.test to run tests (more useful for debugging)

python runtests.py -coverage
  Generate test coverage report. Statistics are written to /tmp

python runtests.py -profile
  Generate profile stats (this is much slower)

python runtests.py -nogmpy
  Run tests without using GMPY even if it exists

python runtests.py -strict
  Enforce extra tests in normalize()

python runtests.py -local
  Insert '../..' at the beginning of sys.path to use local mpmath

Additional arguments are used to filter the tests to run. Only files that have
one of the arguments in their name are executed.

"""

import sys, os, traceback

profile = False
if "-profile" in sys.argv:
    sys.argv.remove('-profile')
    profile = True

coverage = False
if "-coverage" in sys.argv:
    sys.argv.remove('-coverage')
    coverage = True

threads = 1
if "-threads" in sys.argv:
    arg_idx = sys.argv.index('-threads')
    threads = int(sys.argv[arg_idx+1])
    del sys.argv[arg_idx:arg_idx+2]

if "-nogmpy" in sys.argv:
    sys.argv.remove('-nogmpy')
    os.environ['MPMATH_NOGMPY'] = 'Y'

if "-strict" in sys.argv:
    sys.argv.remove('-strict')
    os.environ['MPMATH_STRICT'] = 'Y'

if "-local" in sys.argv:
    sys.argv.remove('-local')
    importdir = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                             '../..'))
else:
    importdir = ''

# TODO: add a flag for this
testdir = ''

def testit(importdir='', testdir=''):
    """Run all tests in testdir while importing from importdir."""
    if importdir:
        sys.path.insert(1, importdir)
    if testdir:
        sys.path.insert(1, testdir)
    import os.path
    import mpmath
    print("mpmath imported from %s" % os.path.dirname(mpmath.__file__))
    print("mpmath backend: %s" % mpmath.libmp.backend.BACKEND)
    print("mpmath mp class: %s" % repr(mpmath.mp))
    print("mpmath version: %s" % mpmath.__version__)
    print("Python version: %s" % sys.version)
    print("")
    if "-py" in sys.argv:
        sys.argv.remove('-py')
        import py
        py.test.cmdline.main()
    else:
        import glob
        from timeit import default_timer as clock
        modules = []
        args = sys.argv[1:]
        # search for tests in directory of this file if not otherwise specified
        if not testdir:
            pattern = os.path.dirname(sys.argv[0])
        else:
            pattern = testdir
        if pattern:
            pattern += '/'
        pattern += 'test*.py'
        # look for tests (respecting specified filter)
        for f in glob.glob(pattern):
            name = os.path.splitext(os.path.basename(f))[0]
            # If run as a script, only run tests given as args, if any are given
            if args and __name__ == "__main__":
                ok = False
                for arg in args:
                    if arg in name:
                        ok = True
                        break
                if not ok:
                    continue
            module = __import__(name)
            priority = module.__dict__.get('priority', 100)
            if priority == 666:
                modules = [[priority, name, module]]
                break
            modules.append([priority, name, module])

        stdout = sys.stdout
        stderr = sys.stderr
        # execute tests
        def runtest(kv):
            f, func = kv
            if f.startswith('test_'):
                if coverage and ('numpy' in f):
                    return
                stdout.write("    " + f[5:].ljust(25) + " ")
                t1 = clock()
                try:
                    func()
                except:
                    etype, evalue, trb = sys.exc_info()
                    if etype in (KeyboardInterrupt, SystemExit):
                        raise
                    print("", file=stdout)
                    print("TEST FAILED!", file=stdout)
                    print("", file=stdout)
                    traceback.print_exc(file=stderr)
                t2 = clock()
                print("ok " + "       " + ("%.7f" % (t2-t1)) + " s", \
                      file=stdout)

        modules.sort()
        tstart = clock()
        for priority, name, module in modules:
            print(name)
            mapargs = (runtest, sorted(module.__dict__.items(), \
                                       key=lambda x: x[0]))
            if threads > 1:
                from multiprocessing import Pool
                with Pool(threads) as pool:
                    pool.map(*mapargs)
            else:
                list(map(*mapargs))
        tend = clock()
        print("")
        print("finished tests in " + ("%.2f" % (tend-tstart)) + " seconds")
        # clean sys.path
        if importdir:
            sys.path.remove(importdir)
        if testdir:
            sys.path.remove(testdir)

if __name__ == '__main__':
    if profile:
        import cProfile
        cProfile.run("testit('%s', '%s')" % (importdir, testdir), sort=1)
    elif coverage:
        import trace
        tracer = trace.Trace(ignoredirs=[sys.prefix, sys.exec_prefix],
            trace=0, count=1)
        tracer.run('testit(importdir, testdir)')
        r = tracer.results()
        r.write_results(show_missing=True, summary=True, coverdir="/tmp")
    else:
        testit(importdir, testdir)
