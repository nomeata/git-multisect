git multisect: Find commits that matter
=======================================

This tool can be thought of as a variant of `git log` that omits those commits that
do not affect the output of a given command. It can also be thought of a variant
of `git bisect` with more than just “bad” and “good” as states.

The motivation application is if you have a project that depends on another
project, and you are bumping the dependency version, and you want to see the changes
done upstream that affect _your_ project. So you instruct `git multisect` to build
it with all upstream changes, and compare the build output.

Intro
-----

### Very small example

Consider this very small git repository, with four commits:
 * A initial commit that adds the `example.sh` program,
 * one that changes its output,
 * one that just refactors the code,
 * but does not change the output, and
 * yet another changing the output

<details>

<summary>Look at each change…</summary>

```
$ git log --oneline --reverse -p
dcf6dae Initial check-in
diff --git a/example.sh b/example.sh
new file mode 100755
index 0000000..d6954d9
--- /dev/null
+++ b/example.sh
@@ -0,0 +1,3 @@
+#!/usr/bin/env bash
+
+echo "Hello World!"
48c68e2 Second version
diff --git a/example.sh b/example.sh
index d6954d9..3f29b95 100755
--- a/example.sh
+++ b/example.sh
@@ -1,3 +1,3 @@
 #!/usr/bin/env bash

-echo "Hello World!"
+echo "Hello Galaxies!"
d25f474 Refactor
diff --git a/example.sh b/example.sh
index 3f29b95..91bee54 100755
--- a/example.sh
+++ b/example.sh
:...skipping...
dcf6dae Initial check-in
diff --git a/example.sh b/example.sh
new file mode 100755
index 0000000..d6954d9
--- /dev/null
+++ b/example.sh
@@ -0,0 +1,3 @@
+#!/usr/bin/env bash
+
+echo "Hello World!"
48c68e2 Second version
diff --git a/example.sh b/example.sh
index d6954d9..3f29b95 100755
--- a/example.sh
+++ b/example.sh
@@ -1,3 +1,3 @@
 #!/usr/bin/env bash

-echo "Hello World!"
+echo "Hello Galaxies!"
d25f474 Refactor
diff --git a/example.sh b/example.sh
index 3f29b95..91bee54 100755
--- a/example.sh
+++ b/example.sh
@@ -1,3 +1,4 @@
 #!/usr/bin/env bash

-echo "Hello Galaxies!"
+who=Galaxies
+echo "Hello $who!"
8764b3f (HEAD -> master) Third version
diff --git a/example.sh b/example.sh
index 91bee54..bd704ea 100755
--- a/example.sh
+++ b/example.sh
@@ -1,4 +1,4 @@
 #!/usr/bin/env bash

-who=Galaxies
+who=Universe
 echo "Hello $who!"
```

</details>

As a user upgrading from `dcf6dae` to the latest verision, we might want to check the changelog:
```
$ git log --oneline
8764b3f (HEAD -> master) Third version
d25f474 Refactor
48c68e2 Second version
dcf6dae Initial check-in
```

But as a user we usually do not care about refactorings; we only care about
those changes that really affect us. So we can use `git-multisect` for that:

```
$ git-multisect.py -f dcf6dae -t master -c 'git checkout -q $REV; ./example.sh'
Found 3 commits
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing dcf6dae ...
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing 8764b3f ...
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing 48c68e2 ...
[3 total, 1 relevant, 0 irrelevant, 0 skipped, 2 unknown] inspecing d25f474 ...
[3 total, 2 relevant, 1 irrelevant, 0 skipped, 0 unknown] done

48c68e2 Second version
8764b3f Third version
```

We tell it the range we are interested, and what to do for each revision
(namely, to check it out and run the script). And very nicely it lists only
those commits that change the output, and omits the refactoring commit..

### A variant of the very small example

Of course, there are other properties of the repsitory we may care about. Maybe we want to know which commits have increased the code size? Let's see

```
$ ../git-multisect.py -f dcf6dae3 -t master --show-output -c 'git cat-file blob $REV:example.sh|wc -c'
Found 3 commits
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing dcf6dae ...
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing 8764b3f ...
[3 total, 0 relevant, 0 irrelevant, 0 skipped, 3 unknown] inspecing 48c68e2 ...
[3 total, 1 relevant, 0 irrelevant, 0 skipped, 2 unknown] inspecing d25f474 ...
[3 total, 2 relevant, 1 irrelevant, 0 skipped, 0 unknown] done

dcf6dae Initial check-in
41
48c68e2 Second version
44
d25f474 Refactor
53
```

In this example, our test command does not have to actually check out the
revision, as it can use `git cat-file`; presumably directly accessing the git
repo this way is faster.

We also use the `--show-output` option to see the output next to the commits.
Note that commit `Third version` is skipped (it did not change the file size,
but now we see the refactoring commit!

### A realistic example

In the following example, I want to know which changes to the nixpkgs package repostory affect my server. The command line is a bit log, so here are the relevant bits:

* The argument to `-f` is the current revision of `nixpkgs` that I am using, which I can query using `nix falke metadata` and a `jq` call to resolve two levels of indirection.
* I want to upgrade to the latest commit on the `release-22.11` branch
* The command that I am running is `nix path-info --derivation`. This prints a
  hash (a store path, actually) of the _recipie_ of building my system. It does
  not actually build the system (which would take longer), but is a good approximation
  for “does this affect my system”.
* I pass `--no-update-lock-file` to not actually touch my configuation.
* And, curcially I use `--override-input` to tell `nix` to use that particular revision.
* With `--hide-stderr` I make it hide the noise that `nix path-info` does on stderr.
* Finally, because most nixpkgs commits are merges and their first line is rather unhelpful, I pass `--log-option=--pretty=medium` to switch to a more elaborate log format.

At the time of writing, there are 39 new commits, but after inspecting 19 of
them, it found that only seven commits are relevant to me. It does not even
look at commits that are between two commits where the program produces the
same output; in this case this saved looking at two commits.

```
$ git-multisect.py \
	-C ~/build/nixpkgs \
	-f $(nix flake metadata ~/nixos --json|jq -r ".locks.nodes[.locks.nodes[.locks.root].inputs.nixpkgs].locked.rev") \
	-t release-22.11 \
	-c 'nix path-info --derivation '\
	   '~/nixos#nixosConfigurations.richard.config.system.build.toplevel '\
	   '--no-update-lock-file '\
	   '--override-input nixpkgs ~/"build/nixpkgs?rev=$REV"' \
	--hide-stderr --log-option=--pretty=medium
```

<details>

<summary>This produces this output</summary>

```
Found 39 commits
[39 total, 0 relevant, 0 irrelevant, 0 skipped, 39 unknown] inspecing 2fb7d74 ...
[39 total, 0 relevant, 0 irrelevant, 0 skipped, 39 unknown] inspecing 569163e ...
[39 total, 0 relevant, 0 irrelevant, 0 skipped, 39 unknown] inspecing 5642ce8 ...
[39 total, 0 relevant, 0 irrelevant, 0 skipped, 39 unknown] inspecing e0c8cf8 ...
[39 total, 0 relevant, 1 irrelevant, 8 skipped, 30 unknown] inspecing 89d0361 ...
[39 total, 0 relevant, 1 irrelevant, 8 skipped, 30 unknown] inspecing d1c7e63 ...
[39 total, 0 relevant, 2 irrelevant, 9 skipped, 28 unknown] inspecing e6d5772 ...
[39 total, 0 relevant, 3 irrelevant, 9 skipped, 27 unknown] inspecing a099526 ...
[39 total, 1 relevant, 4 irrelevant, 9 skipped, 25 unknown] inspecing 854312a ...
[39 total, 1 relevant, 4 irrelevant, 9 skipped, 25 unknown] inspecing f27a4e2 ...
[39 total, 3 relevant, 4 irrelevant, 9 skipped, 23 unknown] inspecing 95043dc ...
[39 total, 4 relevant, 4 irrelevant, 9 skipped, 22 unknown] inspecing 0cf4274 ...
[39 total, 5 relevant, 5 irrelevant, 9 skipped, 20 unknown] inspecing 638ac67 ...
[39 total, 5 relevant, 5 irrelevant, 9 skipped, 20 unknown] inspecing cdd5636 ...
[39 total, 5 relevant, 6 irrelevant, 13 skipped, 15 unknown] inspecing a7af1ab ...
[39 total, 5 relevant, 7 irrelevant, 14 skipped, 13 unknown] inspecing 263bcb3 ...
[39 total, 6 relevant, 8 irrelevant, 15 skipped, 10 unknown] inspecing d07ee65 ...
[39 total, 6 relevant, 9 irrelevant, 19 skipped, 5 unknown] inspecing 2dc8a48 ...
[39 total, 6 relevant, 10 irrelevant, 20 skipped, 3 unknown] inspecing 167d66f ...
[39 total, 6 relevant, 11 irrelevant, 20 skipped, 2 unknown] inspecing c95bf18 ...
[39 total, 7 relevant, 12 irrelevant, 20 skipped, 0 unknown] done

commit a0995268af8ba0336a81344a3bf6a50d6d6481b2
Author: github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>
Date:   Sat Feb 18 10:45:11 2023 -0800

    linux_{5_15,6_1}: revert patch to fix Equinix Metal bonded networking with `ice` driver (#216955)

    Some Equinix Metal instances, such as a3.large.x86, m3.large.x86
    (specific hardware revisions), and n3.large.x86, use the `ice` kernel
    driver for their network cards, in conjunction with bonded devices.
    However, this commit caused a regression where these bonded devices
    would deadlock. This was initially reported by Jaroslav Pulchart on
    the netdev mailing list[1], and there were follow-up patches from Dave
    Ertman[2][3] that attempted to fix this but were not up to snuff for
    various reasons[4].

    Specifically, v2 of the patch ([3]) appears to fix the issue on some
    devices (tested with 8086:159B network cards), while it is still broken
    on others (such as an 8086:1593 network card).

    We revert the patch exposing the issue until upstream has a working
    solution in order to make Equinix Metal instances work reliably again.

    [1]: https://lore.kernel.org/netdev/CAK8fFZ6A_Gphw_3-QMGKEFQk=sfCw1Qmq0TVZK3rtAi7vb621A@mail.gmail.com/
    [2]: https://patchwork.ozlabs.org/project/intel-wired-lan/patch/20230111183145.1497367-1-david.m.ertman@intel.com/
    [3]: https://patchwork.ozlabs.org/project/intel-wired-lan/patch/20230215191757.1826508-1-david.m.ertman@intel.com/
    [4]: https://lore.kernel.org/netdev/cb31a911-ba80-e2dc-231f-851757cfd0b8@intel.com/T/#m6e53f8c43093693c10268140126abe99e082dc1c

    (cherry picked from commit 4e2079b96d281212b695ca557755909799f163ad)

    Co-authored-by: Cole Helbling <cole.helbling@determinate.systems>
commit f27a4e2f6a3a23b843ca1c736e6043fb8b99acc1
Merge: 89d03617610 85b77f73405
Author: Nick Cao <nickcao@nichi.co>
Date:   Sun Feb 19 09:48:52 2023 +0800

    Merge pull request #217008 from NixOS/backport-202245-to-release-22.11

    [Backport release-22.11] nixos/rpcbind: Add dependency for systemd-tmpfiles-setup
commit 854312a89d8de4274d5bce358a7ad71f55a7d29b
Merge: f27a4e2f6a3 ed2f5ad6f0e
Author: Maximilian Bosch <maximilian@mbosch.me>
Date:   Sun Feb 19 11:16:17 2023 +0100

    Merge pull request #217020 from NixOS/backport-209147-to-release-22.11

    [Backport release-22.11] nixos/parsedmarc: fix Grafana provisioning
commit 95043dc713d94d913ca1087f543e185a76e46cd5
Merge: 854312a89d8 13f402f7287
Author: Maximilian Bosch <maximilian@mbosch.me>
Date:   Sun Feb 19 11:23:16 2023 +0100

    Merge pull request #216875 from NixOS/backport-216658-to-release-22.11

    [Backport release-22.11] nixos/tests: sensible test timeouts
commit 0cf4274b5d06325bd16dbf879a30981bc283e58a
Merge: 95043dc713d 532f3aa6052
Author: Pierre Bourdon <delroth@gmail.com>
Date:   Sun Feb 19 23:37:48 2023 +0900

    Merge pull request #217121 from NixOS/backport-216463-to-release-22.11

    [Backport release-22.11] sudo: 1.9.12p2 -> 1.9.13
commit 263bcb3b79ac2cfe7986c6933e0b684a0df05939
Merge: a7af1abd95b 43a7503149f
Author: Kim Lindberger <kim.lindberger@gmail.com>
Date:   Tue Feb 21 15:56:20 2023 +0100

    Merge pull request #217310 from NixOS/backport-215523-to-release-22.11

    [Backport release-22.11] discourse: 2.9.0.beta14 -> 3.1.0.beta2
commit 569163eaeef921fe1932ffcdbecdccf004ae6982 (HEAD -> release-22.11, origin/release-22.11)
Merge: c95bf18beba 019251bbb36
Author: Nick Cao <nickcao@nichi.co>
Date:   Thu Feb 23 09:13:59 2023 +0800

    Merge pull request #217779 from NixOS/backport-217730-to-release-22.11

    [Backport release-22.11] nixos/alps: fix embarrasing typo
```

</details>

Usage
-----

```
Usage: git-multisect.py [options]

Options:
  -h, --help            show this help message and exit
  -C DIR, --repo=DIR    Repository (default .)
  -f REV, --from=REV    First revision
  -t REV, --to=REV      Last revision (default: HEAD)
  --hide-stderr         Hide the command stderr. Good if nosiy
  --show-output         Include the program output after each log line, and
                        include the first commit in the log
  --log-options=LOG_OPTIONS
                        How to print the git log (default: --oneline)
  -c CMD, --cmd=CMD     Command to run. Will be passed to a shell with REV set
                        to a revision.
```

Issues/Roadmap/Caveats/TODO
---------------------------

* The tool requires the first commit to be an ancestor of the last commit, and
  only looks at the first-parent-line from the last commit. This is good enough
  for the usual single-long-running-branch use case, but could be extended to
  handle more complex DAGs better.

* If a command fails, `git-multisect` aborts with a non-pretty error message.
  This could be improved.

* It is designed for small program output, and stores it all in memory. A more
  efficient way is possible, but probably not the bother. If you have large
  output, run it through a hash calculation in the command.

* The tool could be packaged more properly and have a test suite.

* If this turns out to be useful, maybe someone could upstream it with the git project.


Contributions at <https://github.com/nomeata/git-multisect> are welcome!

