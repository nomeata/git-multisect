#!/usr/bin/env python3

import sys
import subprocess
import os
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-C", "--repo", dest="repo", default=".",
                  help="Repository (default .)", metavar="DIR")
parser.add_option("-f", "--from", dest="start",
                  help="First revision", metavar="REV")
parser.add_option("-t", "--to", dest="to", default="HEAD",
                  help="Last revision (default: HEAD)", metavar="REV")
parser.add_option("--hide-stderr", action = "store_true", dest="hidestderr",
                  help="Hide the command stderr. Good if nosiy")
parser.add_option("--show-output", action = "store_true", dest="show_output",
                  help="Include the program output after each log line")
parser.add_option("--log-options", action = "store", dest="log_options",
                  default="--oneline --no-decorate",
                  help="How to print the git log (default: --oneline)")
parser.add_option("-c", "--cmd", dest="cmd",
                  help="Command to run. Will be passed to a shell with REV set to a revision.", metavar="CMD")
#parser.add_option("-q", "--quiet",
#                  action="store_false", dest="verbose", default=True,
#                  help="don't print status messages to stdout")
(options, args) = parser.parse_args()

if options.start is None or options.cmd is None:
    print("The --from and --cmd options are required\n")
    parser.print_help()
    sys.exit(1)


def err(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

def info(msg):
    print(msg, file=sys.stderr)

# Check if the first revision is an ancestor of the last revision
# (and that the repo can be read)
ret = subprocess.run(["git", "-C", options.repo, "merge-base", "--is-ancestor", \
    options.start, options.to])
if ret.returncode == 0:
    pass # good
elif ret.returncode == 1:
    err(f"Revision {options.start} is not an ancestor of {options.to}, giving up")
else:
    err(f"Failed to run: {' '.join(ret.args)}")

# Get the list of revision

commits = subprocess.check_output(["git", "-C", options.repo, "log", "--topo-order", "--reverse", "--first-parent", "--pretty=tformat:%H", f"{options.start}..{options.to}"],text=True).splitlines()

if len(commits) == 0:
    info(f"Found no commits in {options.start}..{options.to}")
    sys.exit(0)

info(f"Found {len(commits)} commits")

# NB! revs indexing is off-by-one compared to commits indexing
start = subprocess.check_output(["git", "-C", options.repo, "rev-parse", options.start], text=True).splitlines()[0]
revs = [start] + commits

# Stats!
# commits found to be relevant
relevant = set()
irrelevant = 0
skipped = 0

def statinfo(msg):
    unknown = len(commits) - len(relevant) - irrelevant - skipped
    info(f"[{len(commits)} total, {len(relevant)} relevant, {irrelevant} irrelevant, {skipped} skipped, {unknown} unknown] {msg}")

# memoized output processing
outputs = {}
def get_output(i):
    if i not in outputs:
        statinfo(f"inspecing {revs[i][:7]} ...")
        outputs[i] = subprocess.check_output(
            options.cmd,
            shell = True,
            env = dict(os.environ, REV=revs[i]),
            stderr = subprocess.DEVNULL if options.hidestderr else None,
            text = options.show_output
        )
    return outputs[i]

# the stack of ranges (indices, inclusive) yet to check for relevant commits.
# invariant: for all entries but the first we do not know if they are relevant,
# but if they are irrelvant, then because of something in the range.
todo = [(0, len(revs)-1)]
while len(todo)>0:
    (i,j) = todo.pop()
    if get_output(i) == get_output(j):
        # no changes in this range: drop range, mark end as irrelvant and intermediate as skipped
        irrelevant += 1
        skipped += j-i-1
    elif j == i + 1:
        # j proven to be relevant
        relevant.add(j-1) # NB index shift
    else:
        # split the range
        k = (i+j)//2
        todo.append((k,j))
        todo.append((i,k))

def git_log(rev):
    subprocess.run([
        "git",
        "--no-pager",
        "-C", options.repo,
        "log", "-n1"] + options.log_options.split() + [rev])


statinfo("done")
info("")
if options.show_output:
    git_log(start)
    sys.stdout.write(get_output(0))
for i, l in enumerate(commits):
    if i in relevant:
        git_log(l)
        if options.show_output:
            sys.stdout.write(get_output(i+1))

