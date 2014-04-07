#!/usr/bin/python3

'''
gdb python script

notes:
    - you should avoid running manually the same target program while this is running, get_process_pid will not like it
'''

import subprocess
import optparse
import threading
import psutil
import time
import os
import sys

####GLOBAL###
exePath="/usr/lib/libreoffice/program/soffice.bin"
exeArgs='--impress --norestore'
#testcasesPath="/mnt/shared/ppt"
crashesPath=""
logsPath=""
fuzzerPath="./radamsa-bin"
fuzzIter=200
fuzzDst="fuzzed"
restoreFlag = False
debugFlag = True
processTimeout=20 #seconds
listfile='filelist.txt'


#############

"""
for every file
fuzz it
iterate fuzzed
check for crashes
close program if nothing happens
"""

def die(msg):
    sys.stderr.write("[ERROR] " + msg + "\n")
    sys.exit(-1)

def debug_msg(msg):
    global debugFlag
    if debugFlag:
        sys.stdout.write('[FUZZER] ' + msg + '\n')
    return

#receive full path of testcase, and dst dir
#write target files
def fuzz_testcase(testcase, fuzzDst):
    global fuzzerPath
    global fuzzIter
    if not os.path.exists(fuzzDst):
        debug_msg("creating dir %s\n" % (fuzzDst))
        os.mkdir(fuzzDst)
    if debugFlag:
        fuzzCmd = "%s -v -n %d -o %s/fuzzed-%%n.ppt %s" % (fuzzerPath, fuzzIter, fuzzDst, testcase)
        debug_msg(fuzzCmd)
    else:
        fuzzCmd = "%s -n %d -o %s/fuzzed-%%n.ppt %s" % (fuzzerPath, fuzzIter, fuzzDst, testcase)
    ret = os.system(fuzzCmd)
    if (ret != 0):
        die("fuzzer failed to run")
    return

def empty_fuzzdir(fuzzDst):
    os.system("rm -rf %s/*" % fuzzDst)

def parse_args():
    parser = optparse.OptionParser("%prog [some opts] [-L filelist]|[-D fuzzdir]")
    parser.add_option("-v", "--debug", help="get debug output", action="store_true", dest="debug", default=True)
    parser.add_option("-s", "--export", help="save filelist.txt ", action="store_true", dest="saveList", default=False)
    parser.add_option("-t", "--nofuzz", help="start fuzzer, dont generate testcases, for TESTING", action="store_true", dest="nofuzz", default=False)
    parser.add_option("-T", "--test", help="don't start fuzzer, for TESTING", action="store_true", dest="testrun", default=False)
    parser.add_option("-S", "--skipto", help="skip to #n iteration", dest="skipto", default=None)
    parser.add_option("-L", "--list", help="read filelist from file", dest="filelist", default=None)
    parser.add_option("-D", "--fuzzdir", help="create filelist from dir", dest="fuzzdir", default=None)
    
    return parser.parse_args()

def main():
    global exePath
    global exeArgs
    global testcasesPath
    global fuzzDst
    global debugFlag
    global listfile
    
    opts, args = parse_args()
    
    debugFlag = opts.debug
    
    if opts.filelist and opts.fuzzdir:
        die("options -L and -D are mutually exclusive")
    if not opts.filelist and not opts.fuzzdir:
        die("dickhead")
    if opts.fuzzdir:
        testcasesPath=opts.fuzzdir
        filelist=os.listdir(testcasesPath)
    if opts.filelist:
        if opts.saveList:
            debug_msg("already loading from filelist, unsetting writing")
            opts.saveList = False
        try:
            lf=open(opts.saveList)
            filelist=lf.read().split('\n')
        except:
            die('Impossible to load file list, check file and syntax')
    
    if not filelist:
        die("no input files were specified")
    
    if opts.saveList:
        debug_msg("saving list of files to %s" % listfile)
        lf = open(listfile)
        lf.write("\n".join([str(i) for i in filelist]))
        lf.close()
    
    if opts.testrun:
        debug_msg("testrun only, exiting")
        sys.exit(0)
    
    #XXX: why is this try here?
    try:
        start=0
        if opts.skipto:
            start=int(opts.skipto)
        for i in range(start,len(filelist)):
            f = filelist[i]
            fpfile="%s/%s" % (testcasesPath, f)
            debug_msg('fuzzing file #%d' % 0)
            if not opts.nofuzz:
                fuzz_testcase(fpfile, fuzzDst)
            for file in os.listdir(fuzzDst):            
                fuzzedcase=fuzzDst + "/v b" + file
                debug_msg("run target with file %s" % fuzzedcase)
                gdb_proc = subprocess.Popen("./launcher.py --batch --args %s %s %s" % (exePath, exeArgs, fuzzedcase), shell="/usr/bin/python")
                mon_proc = subprocess.Popen("./process_monitor.py %s %s" % (exePath, fuzzedcase), shell="/usr/bin/python")
                if not opts.nofuzz:
                    debug_msg("nofuzz set, will not destroy testcases")
                    empty_fuzzdir(fuzzDst)
                if not opts.nofuzz:
                gdb_proc.wait()
                mon_proc.wait()
                debug_msg('Terminated fuzzing %s' % fuzzedcase)
            if opts.nofuzz:
                debug_msg("nofuzz set, will only do first iteration")
                #gdb_proc.kill()
                #mon_proc.kill()
                sys.exit(0)
    except KeyboardInterrupt:
        debug_msg("Ctrl-c detected, exiting")
        try:
            gdb_proc.kill()
            mon_proc.kill()
        except:
            pass
            
        sys.exit(0)


main()